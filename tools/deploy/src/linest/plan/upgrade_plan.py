"""Generate a sequence of deployment steps for a target version."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from linest.bytecode import compute_hash
from linest.errors import UpgradeError
from linest.models.app_family import AppFamily
from linest.steps.append_state_step import AppendStateStep
from linest.steps.deploy_business_app_step import DeployBusinessAppStep
from linest.steps.deploy_state_app_step import DeployStateAppStep
from linest.steps.handoff_step import HandoffStep
from linest.steps.step import Step


class UpgradePlan:
    """A sequence of steps to reach a target business application version."""

    def __init__(
        self,
        family: AppFamily,
        target_version: int,
        contract_bytecode_path: str | None,
        service_bytecode_path: str | None,
        state_contract_bytecode_path: str | None,
        state_service_bytecode_path: str | None,
        operator: str,
        creator_chain_id: str | None = None,
        repo_dir: Path | None = None,
        business_instantiation_argument: dict[str, Any] | None = None,
    ) -> None:
        self.family = family
        self.target_version = target_version
        self.contract_bytecode_path = contract_bytecode_path
        self.service_bytecode_path = service_bytecode_path
        self.state_contract_bytecode_path = state_contract_bytecode_path
        self.state_service_bytecode_path = state_service_bytecode_path
        self.operator = operator
        self.creator_chain_id = creator_chain_id
        self.repo_dir = repo_dir
        self.business_instantiation_argument = business_instantiation_argument
        self.steps: list[Step] = []

        self._build()

    def _build(self) -> None:
        self.family.validate_upgrade_target(self.target_version)

        if not self.family.versions:
            self._build_first_deploy()
            return

        previous_version = self.family.previous_version(self.target_version)
        if previous_version is None:
            raise UpgradeError(
                f"Cannot deploy version {self.target_version} without a previous version"
            )

        previous_record = self.family.get_version(previous_version)

        self._add_deploy_business_app_step()

        for state_app_name in previous_record.state_apps:
            self.steps.append(
                AppendStateStep(
                    family=self.family,
                    business_app_version=self.target_version,
                    state_app_name=state_app_name,
                )
            )

        if self._has_new_state_app():
            new_state_version = self._new_state_version(previous_record.state_apps)
            self._add_state_app_steps(version=new_state_version)

        self.steps.append(
            HandoffStep(
                family=self.family,
                from_version=previous_version,
                to_version=self.target_version,
            )
        )

    def _build_first_deploy(self) -> None:
        if not self._has_business_bytecode():
            raise UpgradeError(
                "First deploy requires --contract-bytecode and --service-bytecode"
            )
        if not self._has_state_bytecode():
            raise UpgradeError(
                "First deploy requires --state-contract-bytecode and --state-service-bytecode"
            )

        self._add_deploy_business_app_step()
        self._add_state_app_steps(version=1)

    def _add_state_app_steps(self, version: int) -> None:
        """Add steps to deploy a state app and append it to the business app."""
        self.steps.append(
            DeployStateAppStep(
                family=self.family,
                version=version,
                contract_bytecode_path=self.state_contract_bytecode_path,
                service_bytecode_path=self.state_service_bytecode_path,
                business_app_version=self.target_version,
                operator=self.operator,
                creator_chain_id=self.creator_chain_id,
                abi_source_hash=self._resolve_abi_source_hash(version),
            )
        )
        self.steps.append(
            AppendStateStep(
                family=self.family,
                business_app_version=self.target_version,
                state_app_name=f"{self.family.name}-state-v{version}",
            )
        )

    def _add_deploy_business_app_step(self) -> None:
        if not self._has_business_bytecode():
            raise UpgradeError(
                f"Version {self.target_version} deploy requires --contract-bytecode and --service-bytecode"
            )
        self.steps.append(
            DeployBusinessAppStep(
                family=self.family,
                version=self.target_version,
                contract_bytecode_path=self.contract_bytecode_path,
                service_bytecode_path=self.service_bytecode_path,
                instantiation_argument=self.business_instantiation_argument,
                creator_chain_id=self.creator_chain_id,
            )
        )

    def _has_business_bytecode(self) -> bool:
        return (
            self.contract_bytecode_path is not None
            and self.service_bytecode_path is not None
        )

    def _has_state_bytecode(self) -> bool:
        return (
            self.state_contract_bytecode_path is not None
            and self.state_service_bytecode_path is not None
        )

    def _has_new_state_app(self) -> bool:
        return self.target_version > 1 and self._has_state_bytecode()

    @staticmethod
    def _new_state_version(existing_state_apps: list[str]) -> int:
        if not existing_state_apps:
            return 1
        # State app names are like "ams-state-v1".
        latest = max(
            int(name.split("-v")[-1])
            for name in existing_state_apps
            if "-v" in name
        )
        return latest + 1

    def _resolve_abi_source_hash(self, version: int) -> str:
        """Resolve the ABI source hash for a state app version by convention."""
        if self.repo_dir is None:
            raise UpgradeError(
                "Deploying a state app requires --repo-dir to locate the ABI source file"
            )
        abi_path = (
            self.repo_dir
            / "abi"
            / "src"
            / self.family.abi_source_dir_name()
            / f"state_v{version}.rs"
        )
        if not abi_path.exists():
            raise UpgradeError(f"ABI source file not found: {abi_path}")
        return compute_hash(str(abi_path))
