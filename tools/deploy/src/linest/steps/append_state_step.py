"""Step to append a state app to a business app."""

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.errors import DeploymentError
from linest.models.app_family import AppFamily, VersionRecord
from linest.models.business_app import BusinessAppDeployment
from linest.models.state_app import StateAppDeployment
from linest.registry import DeploymentRegistry
from linest.steps.step import Step, StepResult


_APPEND_STATE_MUTATION = """
mutation AppendState($stateApplicationId: ApplicationId!) {
    appendState(stateApplicationId: $stateApplicationId)
}
"""


class AppendStateStep(Step):
    """Append a state app to a business app version."""

    def __init__(
        self,
        family: AppFamily,
        business_app_version: int,
        state_app_name: str,
    ) -> None:
        self.family = family
        self.business_app_version = business_app_version
        self.state_app_name = state_app_name
        self.business_app_name = f"{family.name}-v{business_app_version}"

    @property
    def description(self) -> str:
        return f"Append {self.state_app_name} to {self.business_app_name}"

    def execute(
        self,
        registry: DeploymentRegistry,
        linera_client: LineraClient,
        query_client: QueryClient,
    ) -> StepResult:
        business_app = registry.load_business_app(self.business_app_name)
        state_app = registry.load_state_app(self.state_app_name)

        if self._is_already_appended(query_client, business_app, state_app):
            if self.state_app_name not in business_app.state_apps:
                self._update_registry(registry, business_app, [self.state_app_name])
            return StepResult(
                success=True,
                message=f"{self.state_app_name} already appended to {self.business_app_name}",
            )

        linera_client.submit_application_operation(
            chain_id=business_app.creator_chain_id,
            application_id=business_app.application_id,
            mutation=_APPEND_STATE_MUTATION,
            variables={"stateApplicationId": state_app.application_id},
            operation_type=self.family.resolved_operation_type(),
        )

        updated_state_apps = list(business_app.state_apps)
        updated_state_apps.append(self.state_app_name)

        new_business_app = BusinessAppDeployment.create(
            name=business_app.name,
            version=business_app.version,
            network=business_app.network,
            module_id=business_app.module_id,
            application_id=business_app.application_id,
            creator_chain_id=business_app.creator_chain_id,
            contract_bytecode_path=business_app.contract_bytecode_path,
            service_bytecode_path=business_app.service_bytecode_path,
            contract_bytecode_hash=business_app.contract_bytecode_hash,
            service_bytecode_hash=business_app.service_bytecode_hash,
            instantiation_argument=business_app.instantiation_argument,
            state_apps=updated_state_apps,
        )
        registry.save_deployment(new_business_app)

        self._update_registry(registry, business_app, updated_state_apps)

        return StepResult(
            success=True,
            message=f"Appended {self.state_app_name} to {self.business_app_name}",
        )

    def _is_already_appended(
        self,
        query_client: QueryClient,
        business_app: BusinessAppDeployment,
        state_app: StateAppDeployment,
    ) -> bool:
        """Check on-chain whether the state app is already registered."""
        try:
            apps = query_client.query_state_applications(
                business_app.creator_chain_id, business_app.application_id
            )
        except DeploymentError:
            return False
        return any(
            entry.get("applicationId") == state_app.application_id for entry in apps
        )

    def _update_registry(
        self,
        registry: DeploymentRegistry,
        business_app: BusinessAppDeployment,
        state_apps: list[str],
    ) -> None:
        """Update the registry to reflect the current state apps."""
        new_business_app = BusinessAppDeployment.create(
            name=business_app.name,
            version=business_app.version,
            network=business_app.network,
            module_id=business_app.module_id,
            application_id=business_app.application_id,
            creator_chain_id=business_app.creator_chain_id,
            contract_bytecode_path=business_app.contract_bytecode_path,
            service_bytecode_path=business_app.service_bytecode_path,
            contract_bytecode_hash=business_app.contract_bytecode_hash,
            service_bytecode_hash=business_app.service_bytecode_hash,
            instantiation_argument=business_app.instantiation_argument,
            state_apps=state_apps,
        )
        registry.save_deployment(new_business_app)

        version_record = self.family.get_version(self.business_app_version)
        updated_record = VersionRecord(
            business_app=version_record.business_app,
            state_apps=state_apps,
            status=version_record.status,
            handed_off_to=version_record.handed_off_to,
            handed_off_from=version_record.handed_off_from,
        )
        self.family.versions[self.business_app_version] = updated_record
        registry.save_family(self.family)
