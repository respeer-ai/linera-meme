"""Wrapper around the linera CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from linest.client.query_client import QueryClient
from linest.errors import ConfigError, LineraCliError
from linest.retry import RetryPolicy


class LineraClient:
    """Client for invoking the linera command-line tool."""

    def __init__(
        self,
        wallet_dir: str,
        app_name: str,
        wallet_services: dict[str, str] | None = None,
        retry_policy: RetryPolicy | None = None,
    ) -> None:
        self.wallet_dir = Path(wallet_dir)
        self.app_name = app_name
        self.wallet_services = wallet_services or {}
        self.retry_policy = retry_policy or RetryPolicy()

        # Publisher wallet used for publish-module.
        self.publisher_wallet_path = (
            self.wallet_dir / app_name / "creator" / "wallet.json"
        )
        self.publisher_keystore_path = (
            self.wallet_dir / app_name / "creator" / "keystore.json"
        )
        self.publisher_storage_path = (
            f"rocksdb://{self.wallet_dir / app_name / 'creator' / 'client.db'}"
        )

        # Creator wallet used for create-application.
        self.creator_wallet_path = self.wallet_dir / app_name / "0" / "wallet.json"
        self.creator_keystore_path = (
            self.wallet_dir / app_name / "0" / "keystore.json"
        )
        self.creator_storage_path = (
            f"rocksdb://{self.wallet_dir / app_name / '0' / 'client.db'}"
        )

    def default_chain_id(self) -> str:
        """Return the chain tagged as DEFAULT from the creator wallet."""
        result = self._run_creator("wallet", "show")
        return self._extract_default_chain_id(result.stdout)

    @staticmethod
    def _extract_default_chain_id(output: str) -> str:
        """Parse `linera wallet show` output and return the DEFAULT chain ID."""
        lines = output.strip().splitlines()
        current_chain: str | None = None
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Chain ID:"):
                current_chain = stripped.split(":", 1)[1].strip()
            if stripped.startswith("Tags:") and "DEFAULT" in stripped:
                if current_chain is None:
                    raise LineraCliError("DEFAULT tag appeared before Chain ID")
                return current_chain
        raise LineraCliError("Wallet has no DEFAULT chain")

    def wallet_url_for(self, app_name: str) -> str:
        """Return the wallet service URL for the given app family."""
        if app_name not in self.wallet_services:
            raise ConfigError(f"No wallet service URL configured for {app_name}")
        return self.wallet_services[app_name]

    def publish_module(self, contract_path: str, service_path: str) -> str:
        """Publish a module and return the module ID."""
        result = self._run_publisher(
            "publish-module",
            contract_path,
            service_path,
        )
        return self._extract_id(result.stdout)

    def create_application(
        self,
        module_id: str,
        chain_id: str,
        argument: dict[str, Any] | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> str:
        """Create an application and return the application ID."""
        args = ["create-application", module_id, chain_id]

        if argument is not None:
            args.extend(["--json-argument", json.dumps(argument)])
        if parameters is not None:
            args.extend(["--json-parameters", json.dumps(parameters)])

        result = self._run_creator(*args)
        return self._extract_id(result.stdout)

    def call_operation(
        self,
        wallet_url: str,
        chain_id: str,
        application_id: str,
        mutation: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """Submit an operation via the wallet service GraphQL endpoint."""
        client = QueryClient(wallet_url)
        return client.query(chain_id, application_id, mutation, variables)

    def _run_publisher(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a linera CLI command using the publisher wallet."""
        return self._run_with_wallet(
            self.publisher_wallet_path,
            self.publisher_keystore_path,
            self.publisher_storage_path,
            *args,
        )

    def _run_creator(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run a linera CLI command using the creator wallet."""
        return self._run_with_wallet(
            self.creator_wallet_path,
            self.creator_keystore_path,
            self.creator_storage_path,
            *args,
        )

    def _run_with_wallet(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        *args: str,
    ) -> subprocess.CompletedProcess[str]:
        """Run a linera CLI command and return the completed process."""
        command = [
            "linera",
            "--wallet",
            str(wallet_path),
            "--keystore",
            str(keystore_path),
            "--storage",
            storage_path,
            *args,
        ]

        def _execute() -> subprocess.CompletedProcess[str]:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                raise LineraCliError(
                    f"linera command failed: {' '.join(command)}\n{result.stderr}"
                )

            return result

        return self.retry_policy.call(_execute)

    @staticmethod
    def _extract_id(output: str) -> str:
        """Extract the last non-empty line from command output as an ID."""
        lines = output.strip().splitlines()
        if lines:
            return lines[-1].strip()
        raise LineraCliError(f"Could not extract ID from empty output")
