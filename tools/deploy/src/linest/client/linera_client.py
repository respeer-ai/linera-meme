"""Wrapper around the linera CLI."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from linest.errors import ConfigError, LineraCliError
from linest.retry import RetryPolicy


class LineraClient:
    """Client for invoking the linera command-line tool."""

    def __init__(
        self,
        wallet_dir: str,
        app_name: str,
        repo_dir: str | Path | None = None,
        retry_policy: RetryPolicy | None = None,
        command_timeout: float = 120.0,
    ) -> None:
        self.wallet_dir = Path(wallet_dir)
        self.app_name = app_name
        self.retry_policy = retry_policy or RetryPolicy()
        self.command_timeout = command_timeout

        if repo_dir is not None:
            self.operation_type_crate = Path(repo_dir).resolve() / "abi"
        else:
            self.operation_type_crate = None

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

    def wallet_chain_ids(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
    ) -> list[str]:
        """Return all chain IDs present in the wallet."""
        output = self.wallet_show(wallet_path, keystore_path, storage_path)
        return self._extract_chain_ids(output)

    @staticmethod
    def _extract_chain_ids(output: str) -> list[str]:
        """Parse `linera wallet show` output and return all chain IDs."""
        chain_ids: list[str] = []
        for line in output.strip().splitlines():
            stripped = line.strip()
            if stripped.startswith("Chain ID:"):
                chain_ids.append(stripped.split(":", 1)[1].strip())
        return chain_ids

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
                if owner and owner.lower() not in ("no", "no owner key"):
                    return owner
        raise LineraCliError("Wallet has no default owner")

    def show_ownership(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        chain_id: str,
    ) -> dict[str, Any]:
        """Return parsed ownership information for a chain.

        The output format of ``linera show-ownership`` is expected to be::

            Multi-leader rounds: 100
            Owner weights:
              0x<owner1>: 100
              0x<owner2>: 100

        This parser tolerates extra fields and whitespace.
        """
        result = self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "show-ownership",
            "--chain-id",
            chain_id,
        )
        return self._parse_ownership_output(result.stdout)

    @staticmethod
    def _parse_ownership_output(output: str) -> dict[str, Any]:
        """Parse ``linera show-ownership`` output into a dictionary."""
        ownership: dict[str, Any] = {
            "multi_leader_rounds": None,
            "owners": {},
        }
        in_owner_weights = False
        for line in output.strip().splitlines():
            stripped = line.strip()
            if not stripped:
                in_owner_weights = False
                continue

            if stripped.lower().startswith("multi-leader rounds:"):
                value = stripped.split(":", 1)[1].strip()
                try:
                    ownership["multi_leader_rounds"] = int(value)
                except ValueError:
                    ownership["multi_leader_rounds"] = value
                continue

            if stripped.lower().startswith("owner weights"):
                in_owner_weights = True
                continue

            if in_owner_weights and ":" in stripped:
                owner, weight_str = stripped.rsplit(":", 1)
                owner = owner.strip()
                try:
                    weight = int(weight_str.strip())
                except ValueError:
                    weight = weight_str.strip()
                ownership["owners"][owner] = weight

        return ownership

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
        wallet_path.parent.mkdir(parents=True, exist_ok=True)
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

    def keygen(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
    ) -> str:
        """Generate an unassigned key pair and return the public key/owner."""
        result = self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "keygen",
        )
        return result.stdout.strip()

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
        chain_id: str | None = None,
    ) -> None:
        """Process the inbox for a wallet.

        When ``chain_id`` is provided, it is passed as the positional argument
        so the target chain is processed instead of the wallet's default chain.
        """
        args: list[str | Path] = ["process-inbox"]
        if chain_id is not None:
            args.append(chain_id)
        self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            *args,
        )

    def query_balance(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        chain_id: str,
    ) -> float:
        """Return the native-token balance of a chain as a float."""
        self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "sync",
            chain_id,
        )
        result = self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "query-balance",
            chain_id,
        )
        return self._extract_balance(result.stdout)

    @staticmethod
    def _extract_balance(output: str) -> float:
        """Parse the last non-empty line of query-balance output as a float."""
        lines = output.strip().splitlines()
        if not lines:
            raise LineraCliError("Could not extract balance from empty output")
        last_line = lines[-1].strip()
        try:
            return float(last_line)
        except ValueError as exc:
            raise LineraCliError(
                f"Could not parse balance from: {last_line!r}"
            ) from exc

    def transfer(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        from_chain_id: str,
        to_chain_id: str,
        amount: str,
    ) -> None:
        """Transfer native tokens from one chain to another."""
        self._run_with_wallet(
            wallet_path,
            keystore_path,
            storage_path,
            "transfer",
            "--from",
            from_chain_id,
            "--to",
            to_chain_id,
            amount,
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

    def bcs_serialize_application_operation(
        self,
        mutation: str,
        variables: dict[str, Any],
        operation_type: str = "abi::ams::AmsOperation",
    ) -> str:
        """Serialize a GraphQL mutation into BCS bytes using the ABI crate."""
        if self.operation_type_crate is None:
            raise ConfigError(
                "repo_dir is required to locate the ABI crate for operation serialization"
            )

        result = self._run_with_wallet(
            self.creator_wallet_path,
            self.creator_keystore_path,
            self.creator_storage_path,
            "bcs-serilize-application-operation",
            "--operation-type-crate",
            str(self.operation_type_crate),
            "--operation-type",
            operation_type,
            "--query",
            mutation,
            "--variables",
            json.dumps(variables),
        )
        return result.stdout.strip()

    def submit_application_operation(
        self,
        chain_id: str,
        application_id: str,
        mutation: str,
        variables: dict[str, Any],
    ) -> None:
        """Serialize and execute an application operation on a chain.

        The operation is signed with the app family's creator wallet, which must
        own the target chain.
        """
        operation_hex = self.bcs_serialize_application_operation(mutation, variables)
        self._run_with_wallet(
            self.creator_wallet_path,
            self.creator_keystore_path,
            self.creator_storage_path,
            "execute-application-operation",
            "--chain-id",
            chain_id,
            "--application-id",
            application_id,
            "--operation",
            operation_hex,
        )

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
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    check=False,
                    timeout=self.command_timeout,
                )
            except subprocess.TimeoutExpired as exc:
                raise LineraCliError(
                    f"linera command timed out after {self.command_timeout}s: "
                    f"{' '.join(command)}"
                ) from exc

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
        raise LineraCliError("Could not extract ID from empty output")
