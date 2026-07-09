"""Command to deploy or upgrade a business application."""

from __future__ import annotations

from typing import Any

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.command.dry_run_reporter import DryRunReporter
from linest.config import NetworkConfig
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
    ) -> None:
        """Deploy or upgrade the named application to the target version."""
        family = self.registry.load_family(name)

        plan = UpgradePlan(
            family=family,
            target_version=version,
            contract_bytecode_path=contract_bytecode,
            service_bytecode_path=service_bytecode,
            state_contract_bytecode_path=state_contract_bytecode,
            state_service_bytecode_path=state_service_bytecode,
            operator=self.config.operator,
            creator_chain_id=creator_chain_id,
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
