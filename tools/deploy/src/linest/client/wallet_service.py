"""Temporary wallet service for submitting GraphQL mutations."""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

import requests

from linest.errors import LineraCliError


class WalletService:
    """A short-lived `linera service` process used for mutations."""

    def __init__(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        port: int = 41080,
        extra_env: dict[str, str] | None = None,
        log_file: Path | None = None,
    ) -> None:
        self.wallet_path = wallet_path
        self.keystore_path = keystore_path
        self.storage_path = storage_path
        self.port = port
        self.extra_env = extra_env or {}
        self.log_file = log_file
        self._process: subprocess.Popen[str] | None = None

    @property
    def url(self) -> str:
        """Return the GraphQL endpoint URL for this service."""
        return f"http://localhost:{self.port}"

    def start(self) -> str:
        """Start the service and wait until it is ready.

        Returns the service URL.
        """
        if self._process is not None:
            return self.url

        command = [
            "linera",
            "--wallet",
            str(self.wallet_path),
            "--keystore",
            str(self.keystore_path),
            "--storage",
            self.storage_path,
            "service",
            "--port",
            str(self.port),
        ]

        env = os.environ.copy()
        env.update(self.extra_env)

        if self.log_file is not None:
            self.log_file.parent.mkdir(parents=True, exist_ok=True)
            log_handle = self.log_file.open("w", encoding="utf-8")
            stdout = log_handle
            stderr = subprocess.STDOUT
        else:
            stdout = subprocess.PIPE
            stderr = subprocess.PIPE

        self._process = subprocess.Popen(
            command,
            stdout=stdout,
            stderr=stderr,
            text=True,
            env=env,
        )

        self._wait_ready(command)
        return self.url

    def _wait_ready(self, command: list[str]) -> None:
        """Poll the service health endpoint until it responds.

        This waits indefinitely so that wallets with many chains (e.g. after
        several local deployments or upgrades) can finish initialization before
        downstream steps depend on the service.
        """
        payload = {"query": "query { chains { list } }"}
        attempt = 0

        while True:
            if self._process is None:
                raise LineraCliError("Wallet service process disappeared")

            returncode = self._process.poll()
            if returncode is not None:
                stdout = self._process.stdout.read() if self._process.stdout else ""
                stderr = self._process.stderr.read() if self._process.stderr else ""
                raise LineraCliError(
                    f"Wallet service exited early (code {returncode}): "
                    f"{' '.join(command)}\n{stdout}\n{stderr}"
                )

            try:
                response = requests.post(
                    self.url,
                    json=payload,
                    timeout=2,
                )
                if response.status_code == 200 and "data" in response.json():
                    return
            except Exception:
                pass

            attempt += 1
            if attempt % 10 == 0:
                print(
                    f"Waiting for query service to become ready "
                    f"(attempt {attempt}, url={self.url})...",
                    flush=True,
                )

            time.sleep(1)

    def stop(self) -> None:
        """Terminate the service process."""
        process = self._process
        self._process = None
        if process is None:
            return

        try:
            process.terminate()
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        except Exception:
            pass

    def __enter__(self) -> "WalletService":
        self.start()
        return self

    def __exit__(self, *exc: Any) -> None:
        self.stop()
