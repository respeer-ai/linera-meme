"""Command to deploy or upgrade a business application."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from linest.client.chain_manager import MultiOwnerChainManager
from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.client.wallet_layout import AppWalletLayout
from linest.client.wallet_manager import WalletManager
from linest.command.dry_run_reporter import DryRunReporter
from linest.command.post_deploy_sync import PostDeploySync
from linest.config import NetworkConfig
from linest.errors import DeploymentError, LinestError
from linest.models.app_family import AppFamily
from linest.plan.upgrade_plan import UpgradePlan
from linest.registry import DeploymentRegistry
from linest.steps.append_state_step import AppendStateStep
from linest.steps.deploy_business_app_step import DeployBusinessAppStep
from linest.steps.deploy_state_app_step import DeployStateAppStep
from linest.steps.handoff_step import HandoffStep
from linest.steps.step import StepResult


@dataclass
class DeployResult:
    """Outcome of a single deploy/upgrade attempt."""

    name: str
    version: int
    status: str  # "skipped", "deployed", "failed"
    messages: list[str] = field(default_factory=list)
    error: Exception | None = None

    def __str__(self) -> str:
        lines = [f"[{self.status.upper()}] {self.name} v{self.version}"]
        for message in self.messages:
            lines.append(f"  {message}")
        if self.error is not None:
            lines.append(f"  error: {self.error}")
        return "\n".join(lines)


class DeployCommand:
    """Deploy or upgrade a business application to a target version."""

    def __init__(
        self,
        config: NetworkConfig,
        registry: DeploymentRegistry,
        linera_client: LineraClient,
        query_client: QueryClient,
        base_dir: Path | None = None,
    ) -> None:
        self.config = config
        self.registry = registry
        self.linera_client = linera_client
        self.query_client = query_client
        self.base_dir = base_dir

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
        operation_type: str | None = None,
        no_business_argument: bool = False,
        business_argument: str | None = None,
        bytecode_only: bool = False,
    ) -> DeployResult:
        """Deploy or upgrade the named application to the target version.

        Returns a DeployResult describing whether the deployment was skipped,
        completed, or failed. The result is also printed before returning.
        """
        family = self.registry.load_family(name)
        if operation_type is not None:
            family.operation_type = operation_type
        if bytecode_only:
            family.bytecode_only = True
        self.registry.save_family(family)

        result = DeployResult(name=name, version=version, status="in_progress")

        if version <= family.current_version:
            result.status = "skipped"
            result.messages.append(
                f"current version is {family.current_version}; nothing to do"
            )
            print(result)
            return result

        if not ensure_wallet and creator_chain_id is None:
            creator_chain_id = family.creator_chain_id

        if ensure_wallet:
            if faucet_url is None:
                result.error = LinestError("--ensure-wallet requires --faucet-url")
                print(result)
                return result
            result = self._prepare_wallet_and_chain(
                result=result,
                family=family,
                faucet_url=faucet_url,
                wallet_owner_count=wallet_owner_count,
            )
            if result.status == "failed":
                return result
            creator_chain_id = family.creator_chain_id

        if business_argument is not None:
            business_instantiation_argument = json.loads(business_argument)
        elif no_business_argument:
            business_instantiation_argument = None
        else:
            business_instantiation_argument = {}

        result = self._build_and_execute_plan(
            result=result,
            family=family,
            version=version,
            contract_bytecode=contract_bytecode,
            service_bytecode=service_bytecode,
            state_contract_bytecode=state_contract_bytecode,
            state_service_bytecode=state_service_bytecode,
            creator_chain_id=creator_chain_id,
            repo_dir=repo_dir,
            dry_run=dry_run,
            business_instantiation_argument=business_instantiation_argument,
            bytecode_only=bytecode_only,
        )
        if result.status == "failed":
            return result

        if not bytecode_only:
            result = self._post_deploy_sync(
                result=result,
                family=family,
                wallet_owner_count=wallet_owner_count if ensure_wallet else len(family.owners),
            )
        else:
            result.status = "deployed"
            result.messages.append("bytecode registration completed")
            print(result)
        return result

    def _prepare_wallet_and_chain(
        self,
        result: DeployResult,
        family: AppFamily,
        faucet_url: str,
        wallet_owner_count: int,
    ) -> DeployResult:
        """Ensure wallets and the multi-owner chain exist."""
        try:
            creator_owner, owners = WalletManager(
                wallet_dir=self.config.wallet_dir,
                app_name=family.name,
                faucet_url=faucet_url,
                linera_client=self.linera_client,
                owner_count=wallet_owner_count,
                existing_owners=family.owners,
            ).ensure_wallets()
            resolved_chain_id = MultiOwnerChainManager(
                wallet_dir=self.config.wallet_dir,
                app_name=family.name,
                linera_client=self.linera_client,
                base_dir=self.base_dir,
                env=self.config.env,
                faucet_url=faucet_url,
            ).ensure_chain(
                family=family,
                creator_owner=creator_owner,
                owners=owners,
            )
            if family.creator_chain_id is not None and family.creator_chain_id != resolved_chain_id:
                raise DeploymentError(
                    f"Creator chain mismatch: expected {family.creator_chain_id}, "
                    f"resolved to {resolved_chain_id}"
                )
            self.registry.save_family(family)
        except Exception as exc:
            result.status = "failed"
            result.error = exc
            result.messages.append(f"wallet/chain preparation failed: {exc}")
            print(result)
        return result

    def _build_and_execute_plan(
        self,
        result: DeployResult,
        family: AppFamily,
        version: int,
        contract_bytecode: str | None,
        service_bytecode: str | None,
        state_contract_bytecode: str | None,
        state_service_bytecode: str | None,
        creator_chain_id: str | None,
        repo_dir: Path | None,
        dry_run: bool,
        business_instantiation_argument: dict[str, Any] | None = None,
        bytecode_only: bool = False,
    ) -> DeployResult:
        """Build the upgrade plan and execute its steps."""
        try:
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
                business_instantiation_argument=business_instantiation_argument,
                bytecode_only=bytecode_only,
            )
        except Exception as exc:
            result.status = "failed"
            result.error = exc
            result.messages.append(f"upgrade planning failed: {exc}")
            print(result)
            return result

        if dry_run:
            DryRunReporter().report(plan)
            result.status = "skipped"
            result.messages.append("dry run completed")
            print(result)
            return result

        for step in plan.steps:
            print(f"-> {step.description}")
            result = self._execute_step(result, step)
            if result.status == "failed":
                return result

        family.current_version = version
        self.registry.save_family(family)
        return result

    def _execute_step(
        self,
        result: DeployResult,
        step: Any,
    ) -> DeployResult:
        """Execute a single deployment step and record the outcome."""
        try:
            step_result = step.execute(
                registry=self.registry,
                linera_client=self.linera_client,
                query_client=self.query_client,
            )
        except Exception as exc:
            result.status = "failed"
            result.error = exc
            result.messages.append(f"step '{step.description}' failed: {exc}")
            print(result)
            return result

        if not step_result.success:
            result.status = "failed"
            result.error = RuntimeError(step_result.message)
            result.messages.append(
                f"step '{step.description}' failed: {step_result.message}"
            )
            print(result)
            return result

        print(f"   {step_result.message}")
        result.messages.append(f"{step.description}: {step_result.message}")
        return result

    def _post_deploy_sync(
        self,
        result: DeployResult,
        family: AppFamily,
        wallet_owner_count: int,
    ) -> DeployResult:
        """Run post-deployment synchronization steps."""
        try:
            PostDeploySync(
                config=self.config,
                linera_client=self.linera_client,
                query_client=self.query_client,
            ).sync(
                family=family,
                wallet_dir=Path(self.config.wallet_dir),
                owner_count=wallet_owner_count,
            )
        except Exception as exc:
            result.status = "failed"
            result.error = exc
            result.messages.append(f"post-deploy sync failed: {exc}")
            print(result)
            return result

        result.status = "deployed"
        result.messages.append("deployment completed")
        print(result)
        return result

    def _operator_owner(self) -> str:
        """Return the operator owner string from the network config."""
        operator = self.config.operator
        if isinstance(operator, dict):
            return str(operator.get("owner", operator))
        return str(operator)
