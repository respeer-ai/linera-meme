"""Command to deploy or upgrade a business application."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from linest.client.chain_manager import MultiOwnerChainManager
from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.client.wallet_manager import WalletManager
from linest.command.dry_run_reporter import DryRunReporter
from linest.config import NetworkConfig
from linest.errors import DeploymentError, LinestError
from linest.plan.upgrade_plan import UpgradePlan
from linest.registry import DeploymentRegistry
from linest.steps.step import StepResult


class DeployCommand:
    """Deploy or upgrade a business application to a target version."""

    def __init__(
        self,
        config: NetworkConfig,
        registry: DeploymentRegistry,
        linera_client: LineraClient,
        query_client: QueryClient,
    ) -> None:
        self.config = config
        self.registry = registry
        self.linera_client = linera_client
        self.query_client = query_client

    def deploy(
        self,
        name: str,
        version: int,
        contract_bytecode: str | None,
        service_bytecode: str | None,
        state_contract_bytecode: str | None,
        state_service_bytecode: str | None,
        dry_run: bool,
        creator_chain_id: str | None = None,
        repo_dir: Path | None = None,
        ensure_wallet: bool = False,
        faucet_url: str | None = None,
        wallet_owner_count: int = 1,
    ) -> None:
        """Deploy or upgrade the named application to the target version."""
        family = self.registry.load_family(name)

        if not ensure_wallet and creator_chain_id is None:
            creator_chain_id = family.creator_chain_id

        if ensure_wallet:
            if faucet_url is None:
                raise LinestError("--ensure-wallet requires --faucet-url")
            creator_owner, owners = WalletManager(
                wallet_dir=self.config.wallet_dir,
                app_name=name,
                faucet_url=faucet_url,
                linera_client=self.linera_client,
                owner_count=wallet_owner_count,
            ).ensure_wallets()
            resolved_chain_id = MultiOwnerChainManager(
                wallet_dir=self.config.wallet_dir,
                app_name=name,
                linera_client=self.linera_client,
            ).ensure_chain(
                family=family,
                creator_owner=creator_owner,
                owners=owners,
            )
            if creator_chain_id is not None and creator_chain_id != resolved_chain_id:
                raise DeploymentError(
                    f"Creator chain mismatch: expected {creator_chain_id}, "
                    f"registry has {resolved_chain_id}"
                )
            creator_chain_id = resolved_chain_id
            self.registry.save_family(family)

        plan = UpgradePlan(
            family=family,
            target_version=version,
            contract_bytecode_path=contract_bytecode,
            service_bytecode_path=service_bytecode,
            state_contract_bytecode_path=state_contract_bytecode,
            state_service_bytecode_path=state_service_bytecode,
            operator=self._operator_owner(),
            creator_chain_id=creator_chain_id,
            repo_dir=repo_dir,
        )

        if dry_run:
            DryRunReporter().report(plan)
            return

        for step in plan.steps:
            print(f"-> {step.description}")
            result = step.execute(
                registry=self.registry,
                linera_client=self.linera_client,
                query_client=self.query_client,
            )
            if not result.success:
                raise RuntimeError(result.message)
            print(f"   {result.message}")

        family.current_version = version
        self.registry.save_family(family)

    def _operator_owner(self) -> str:
        """Return the operator owner string from the network config."""
        operator = self.config.operator
        if isinstance(operator, dict):
            return str(operator.get("owner", operator))
        return str(operator)
