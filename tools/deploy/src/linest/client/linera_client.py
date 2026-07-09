"""Wrapper around the linera CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from linest.client.query_client import QueryClient
from linest.client.wallet_service import WalletService
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
        self._managed_service: WalletService | None = None

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
        return self.default_chain_id_for(
            self.creator_wallet_path,
            self.creator_keystore_path,
            self.creator_storage_path,
        )

    def default_chain_id_for(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
    ) -> str:
        """Return the chain tagged as DEFAULT from the given wallet."""
        result = self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "wallet",
            "show",
        )
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
        """Return the wallet service URL for the given app family.

        If no external service is configured for the current app family, start
        a temporary local service on the creator wallet.
        """
        if app_name in self.wallet_services:
            return self.wallet_services[app_name]

        if app_name != self.app_name:
            raise ConfigError(f"No wallet service URL configured for {app_name}")

        if self._managed_service is None:
            self._managed_service = WalletService(
                wallet_path=self.creator_wallet_path,
                keystore_path=self.creator_keystore_path,
                storage_path=self.creator_storage_path,
            )
            self._managed_service.start()

        return self._managed_service.url

    def stop_wallet_service(self) -> None:
        """Stop any temporary wallet service started by this client."""
        if self._managed_service is not None:
            self._managed_service.stop()
            self._managed_service = None

    def wallet_show(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
    ) -> str:
        """Run `linera wallet show` and return stdout.

        Raises LineraCliError if the wallet is missing or corrupt.
        """
        result = self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "wallet",
            "show",
        )
        return result.stdout

    def default_owner(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
    ) -> str:
        """Return the default owner of a wallet."""
        output = self.wallet_show(wallet_path, keystore_path, storage_path)
        return self._extract_default_owner(output)

    @staticmethod
    def _extract_default_owner(output: str) -> str:
        """Parse `linera wallet show` output and return the DEFAULT owner."""
        lines = output.strip().splitlines()
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("Default owner:"):
                owner = stripped.split(":", 1)[1].strip()
                if owner and owner.lower() != "no":
                    return owner
        raise LineraCliError("Wallet has no default owner")

    def open_multi_owner_chain(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        from_chain_id: str,
        owners: list[str],
        multi_leader_rounds: int = 100,
        initial_balance: str = "20.",
    ) -> str:
        """Open a multi-owner chain and return the new chain ID."""
        owner_weights = {owner: 100 for owner in owners}
        result = self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "open-multi-owner-chain",
            "--from",
            from_chain_id,
            "--owners",
            json.dumps(owner_weights),
            "--multi-leader-rounds",
            str(multi_leader_rounds),
            "--initial-balance",
            initial_balance,
        )
        return self._extract_id(result.stdout)

    def assign_chain(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        owner: str,
        chain_id: str,
    ) -> None:
        """Assign a chain to an owner in a wallet."""
        self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "assign",
            "--owner",
            owner,
            "--chain-id",
            chain_id,
        )

    def init_wallet(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        faucet_url: str,
    ) -> None:
        """Initialize a new wallet from a faucet."""
        self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "wallet",
            "init",
            "--faucet",
            faucet_url,
        )

    def request_chain(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        faucet_url: str,
    ) -> None:
        """Request a default chain for a wallet from a faucet."""
        self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "wallet",
            "request-chain",
            "--faucet",
            faucet_url,
        )

    def publish_module(self, contract_path: str, service_path: str) -> str:
        """Publish a module and return the module ID."""
        result = self._run_publisher(
            "publish-module",
            contract_path,
            service_path,
        )
        return self._extract_id(result.stdout)

    def process_inbox(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
    ) -> None:
        """Process the inbox for a wallet."""
        self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "process-inbox",
        )

    def change_ownership(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        chain_id: str,
        owners: dict[str, int],
        multi_leader_rounds: int = 0,
    ) -> None:
        """Change the ownership of a chain to a set of owners."""
        self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "change-ownership",
            "--chain-id",
            chain_id,
            "--owners",
            json.dumps(owners),
            "--multi-leader-rounds",
            str(multi_leader_rounds),
        )

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
