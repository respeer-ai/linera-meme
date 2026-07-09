"""Step to deploy a typed state application."""

from __future__ import annotations

from typing import Any

from linest.bytecode import compute_hash
from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.errors import DeploymentError, RegistryError
from linest.models.app_family import AppFamily
from linest.models.state_app import StateAppDeployment
from linest.registry import DeploymentRegistry
from linest.steps.step import Step, StepResult


class DeployStateAppStep(Step):
    """Deploy a state app if it is not already in the registry."""

    def __init__(
        self,
        family: AppFamily,
        version: int,
        contract_bytecode_path: str,
        service_bytecode_path: str,
        business_app_version: int,
        operator: str,
        creator_chain_id: str | None = None,
        abi_source_hash: str | None = None,
    ) -> None:
        self.family = family
        self.version = version
        self.contract_bytecode_path = contract_bytecode_path
        self.service_bytecode_path = service_bytecode_path
        self.business_app_version = business_app_version
        self.operator = operator
        self.creator_chain_id = creator_chain_id
        self.abi_source_hash = abi_source_hash
        self.deployment_name = f"{family.name}-state-v{version}"

    @property
    def description(self) -> str:
        return f"Deploy state app {self.deployment_name}"

    def execute(
        self,
        registry: DeploymentRegistry,
        linera_client: LineraClient,
        query_client: QueryClient,
    ) -> StepResult:
        try:
            existing = registry.load_state_app(self.deployment_name)
            if self._bytecode_matches(existing):
                return StepResult(
                    success=True,
                    message=f"State app {self.deployment_name} already deployed",
                )
            raise DeploymentError(
                f"State app {self.deployment_name} exists with different identity"
            )
        except RegistryError:
            pass

        business_app_name = f"{self.family.name}-v{self.business_app_version}"
        business_app = registry.load_business_app(business_app_name)

        module_id = linera_client.publish_module(
            self.contract_bytecode_path,
            self.service_bytecode_path,
        )

        creator_chain_id = self.creator_chain_id or linera_client.default_chain_id()
        instantiation_argument = {
            "business_application_id": business_app.application_id,
            "operator": self.operator,
        }
        application_id = linera_client.create_application(
            module_id=module_id,
            chain_id=creator_chain_id,
            argument=instantiation_argument,
        )

        deployment = StateAppDeployment.create(
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
            business_application_id=business_app.application_id,
            instantiation_argument=instantiation_argument,
            abi_source_hash=self.abi_source_hash,
        )

        registry.save_deployment(deployment)

        return StepResult(
            success=True,
            message=f"Deployed state app {self.deployment_name} as {application_id}",
        )

    def _bytecode_matches(self, deployment: StateAppDeployment) -> bool:
        if self.abi_source_hash is None:
            raise DeploymentError(
                "State app deploy requires an ABI source hash"
            )
        if deployment.abi_source_hash is None:
            return False
        return deployment.abi_source_hash == self.abi_source_hash
