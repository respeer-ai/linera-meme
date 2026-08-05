"""Step to register bytecode module ids without creating applications."""

from __future__ import annotations

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.models.app_family import AppFamily
from linest.registry import DeploymentRegistry
from linest.steps.step import Step, StepResult


class RegisterBytecodeStep(Step):
    """Publish business and state bytecodes and record their module ids.

    This step is used for ``bytecode_only`` app families where the actual
    applications are created later by another on-chain contract (e.g. proxy).
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
    ) -> None:
        self.family = family
        self.version = version
        self.business_contract_bytecode_path = business_contract_bytecode_path
        self.business_service_bytecode_path = business_service_bytecode_path
        self.state_contract_bytecode_path = state_contract_bytecode_path
        self.state_service_bytecode_path = state_service_bytecode_path
        self.previous_version = previous_version

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
        if self.previous_version is not None:
            previous_record = self.family.versions[self.previous_version]
            previous_state_module_ids = list(previous_record.state_module_ids)

        business_module_id = linera_client.publish_module(
            self.business_contract_bytecode_path,
            self.business_service_bytecode_path,
        )
        state_module_id = linera_client.publish_module(
            self.state_contract_bytecode_path,
            self.state_service_bytecode_path,
        )

        self.family.add_version(
            version=self.version,
            status="registered",
            business_module_id=business_module_id,
            state_module_ids=previous_state_module_ids + [state_module_id],
        )
        registry.save_family(self.family)

        return StepResult(
            success=True,
            message=(
                f"Registered business module {business_module_id} "
                f"and state module {state_module_id} for v{self.version}"
            ),
        )
