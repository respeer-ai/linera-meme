"""Step to register bytecode module ids without creating applications."""

from __future__ import annotations

from pathlib import Path

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.models.app_family import AppFamily, VersionRecord
from linest.registry import DeploymentRegistry
from linest.steps.step import Step, StepResult
from linest.version import read_state_crate_version


class RegisterBytecodeStep(Step):
    """Publish business and state bytecodes and record their module ids.

    This step is used for ``bytecode_only`` app families where the actual
    applications are created later by another on-chain contract (e.g. proxy).
    State bytecode is only published when the state crate version changes;
    otherwise the previous version's state module ids are reused.
    """

    def __init__(
        self,
        family: AppFamily,
        version: int,
        business_contract_bytecode_path: str,
        business_service_bytecode_path: str,
        state_contract_bytecode_path: str,
        state_service_bytecode_path: str,
        previous_version: int | None = None,
        repo_dir: Path | None = None,
    ) -> None:
        self.family = family
        self.version = version
        self.business_contract_bytecode_path = business_contract_bytecode_path
        self.business_service_bytecode_path = business_service_bytecode_path
        self.state_contract_bytecode_path = state_contract_bytecode_path
        self.state_service_bytecode_path = state_service_bytecode_path
        self.previous_version = previous_version
        self.repo_dir = repo_dir

    @property
    def description(self) -> str:
        return f"Register bytecode modules for {self.family.name}-v{self.version}"

    def execute(
        self,
        registry: DeploymentRegistry,
        linera_client: LineraClient,
        query_client: QueryClient,
    ) -> StepResult:
        if self.version in self.family.versions:
            return StepResult(
                success=True,
                message=f"Bytecode modules for v{self.version} already registered",
            )

        previous_state_module_ids: list[str] = []
        previous_state_crate_version: int | None = None
        if self.previous_version is not None:
            previous_record = self.family.versions[self.previous_version]
            previous_state_module_ids = list(previous_record.state_module_ids)
            previous_state_crate_version = previous_record.state_crate_version

        state_crate_version = self._state_crate_version()

        # Backfill legacy records that were created before state_crate_version
        # was tracked. Assume the current state crate version matches what was
        # used for the previous version, so state can be reused.
        if self.previous_version is not None and previous_state_crate_version is None:
            previous_state_crate_version = state_crate_version
            self.family.versions[self.previous_version] = VersionRecord(
                business_app=previous_record.business_app,
                state_apps=list(previous_record.state_apps),
                status=previous_record.status,
                handed_off_to=previous_record.handed_off_to,
                handed_off_from=previous_record.handed_off_from,
                business_module_id=previous_record.business_module_id,
                state_module_ids=list(previous_record.state_module_ids),
                state_crate_version=state_crate_version,
            )
        reuse_state = (
            previous_state_crate_version is not None
            and state_crate_version == previous_state_crate_version
        )

        business_module_id = linera_client.publish_module(
            self.business_contract_bytecode_path,
            self.business_service_bytecode_path,
        )

        if reuse_state:
            state_module_id = previous_state_module_ids[-1] if previous_state_module_ids else ""
            state_module_ids = list(previous_state_module_ids)
            message = (
                f"Registered business module {business_module_id}; "
                f"reused state modules from v{self.previous_version}"
            )
        else:
            state_module_id = linera_client.publish_module(
                self.state_contract_bytecode_path,
                self.state_service_bytecode_path,
            )
            state_module_ids = previous_state_module_ids + [state_module_id]
            message = (
                f"Registered business module {business_module_id} "
                f"and state module {state_module_id} for v{self.version}"
            )

        self.family.add_version(
            version=self.version,
            status="registered",
            business_module_id=business_module_id,
            state_module_ids=state_module_ids,
            state_crate_version=state_crate_version,
        )
        registry.save_family(self.family)

        return StepResult(success=True, message=message)

    def _state_crate_version(self) -> int:
        if self.repo_dir is None:
            raise RuntimeError(
                "RegisterBytecodeStep requires repo_dir to read state crate version"
            )
        return read_state_crate_version(self.repo_dir, self.family.name)
