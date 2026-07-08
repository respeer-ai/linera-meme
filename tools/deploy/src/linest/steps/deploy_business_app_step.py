"""Step to deploy a business application."""

from __future__ import annotations

from typing import Any

from linest.bytecode import compute_hash
from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.errors import DeploymentError, RegistryError
from linest.models.app_family import AppFamily
from linest.models.business_app import BusinessAppDeployment
from linest.registry import DeploymentRegistry
from linest.steps.step import Step, StepResult


class DeployBusinessAppStep(Step):
    """Deploy a business app if it is not already in the registry."""

    def __init__(
        self,
        family: AppFamily,
        version: int,
        contract_bytecode_path: str,
        service_bytecode_path: str,
        instantiation_argument: dict[str, Any],
        creator_chain_id: str | None = None,
    ) -> None:
        self.family = family
        self.version = version
        self.contract_bytecode_path = contract_bytecode_path
        self.service_bytecode_path = service_bytecode_path
        self.instantiation_argument = instantiation_argument
        self.creator_chain_id = creator_chain_id
        self.deployment_name = f"{family.name}-v{version}"

    @property
    def description(self) -> str:
        return f"Deploy business app {self.deployment_name}"

    def execute(
        self,
        registry: DeploymentRegistry,
        linera_client: LineraClient,
        query_client: QueryClient,
    ) -> StepResult:
        try:
            existing = registry.load_business_app(self.deployment_name)
            if self._bytecode_matches(existing):
                return StepResult(
                    success=True,
                    message=f"Business app {self.deployment_name} already deployed",
                )
            raise DeploymentError(
                f"Business app {self.deployment_name} exists with different bytecode"
            )
        except RegistryError:
            pass

        module_id = linera_client.publish_module(
            self.contract_bytecode_path,
            self.service_bytecode_path,
        )

        creator_chain_id = self.creator_chain_id or linera_client.default_chain_id()
        application_id = linera_client.create_application(
            module_id=module_id,
            chain_id=creator_chain_id,
            argument=self.instantiation_argument,
        )

        deployment = BusinessAppDeployment.create(
            name=self.deployment_name,
            version=self.version,
            network=self.family.env,
            module_id=module_id,
            application_id=application_id,
            creator_chain_id=creator_chain_id,
            contract_bytecode_path=self.contract_bytecode_path,
            service_bytecode_path=self.service_bytecode_path,
            contract_bytecode_hash=compute_hash(self.contract_bytecode_path),
            service_bytecode_hash=compute_hash(self.service_bytecode_path),
            instantiation_argument=self.instantiation_argument,
        )

        registry.save_deployment(deployment)
        self.family.add_version(
            version=self.version,
            business_app=deployment.name,
            state_apps=[],
            status="deployed",
        )
        registry.save_family(self.family)

        return StepResult(
            success=True,
            message=f"Deployed business app {self.deployment_name} as {application_id}",
        )

    def _bytecode_matches(self, deployment: BusinessAppDeployment) -> bool:
        return (
            deployment.contract_bytecode_hash
            == compute_hash(self.contract_bytecode_path)
            and deployment.service_bytecode_hash
            == compute_hash(self.service_bytecode_path)
        )
