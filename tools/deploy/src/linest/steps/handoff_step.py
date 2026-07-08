"""Step to hand off state apps from an old business app to a new one."""

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.models.app_family import AppFamily, VersionRecord
from linest.models.business_app import BusinessAppDeployment
from linest.registry import DeploymentRegistry
from linest.steps.step import Step, StepResult


_HANDOFF_MUTATION = """
mutation Handoff($newBusinessApplicationId: ApplicationId!) {
    handoff(newBusinessApplicationId: $newBusinessApplicationId)
}
"""


class HandoffStep(Step):
    """Hand off all owned state apps from an old business app to a new one."""

    def __init__(
        self,
        family: AppFamily,
        from_version: int,
        to_version: int,
    ) -> None:
        self.family = family
        self.from_version = from_version
        self.to_version = to_version
        self.from_app_name = f"{family.name}-v{from_version}"
        self.to_app_name = f"{family.name}-v{to_version}"

    @property
    def description(self) -> str:
        return (
            f"Hand off state apps from {self.from_app_name} to {self.to_app_name}"
        )

    def execute(
        self,
        registry: DeploymentRegistry,
        linera_client: LineraClient,
        query_client: QueryClient,
    ) -> StepResult:
        from_app = registry.load_business_app(self.from_app_name)
        to_app = registry.load_business_app(self.to_app_name)

        if self._handoff_already_complete(query_client, registry, from_app, to_app):
            self._mark_handoff_complete(registry)
            return StepResult(
                success=True,
                message=f"Handoff from {self.from_app_name} already completed",
            )

        wallet_url = linera_client.wallet_url_for(self.family.name)
        linera_client.call_operation(
            wallet_url=wallet_url,
            chain_id=from_app.creator_chain_id,
            application_id=from_app.application_id,
            mutation=_HANDOFF_MUTATION,
            variables={"newBusinessApplicationId": to_app.application_id},
        )

        self._mark_handoff_complete(registry)

        return StepResult(
            success=True,
            message=f"Handed off state apps from {self.from_app_name} to {self.to_app_name}",
        )

    def _handoff_already_complete(
        self,
        query_client: QueryClient,
        registry: DeploymentRegistry,
        from_app: BusinessAppDeployment,
        to_app: BusinessAppDeployment,
    ) -> bool:
        """Check whether the first state app already points to the new business app."""
        if not from_app.state_apps:
            return False
        first_state_app_name = from_app.state_apps[0]
        try:
            state_app = registry.load_state_app(first_state_app_name)
        except Exception:
            return False
        try:
            current_business_id = query_client.query_business_application_id(
                state_app.creator_chain_id, state_app.application_id
            )
        except Exception:
            return False
        return current_business_id == to_app.application_id

    def _mark_handoff_complete(self, registry: DeploymentRegistry) -> None:
        """Update the registry to reflect a completed handoff."""
        from_record = self.family.get_version(self.from_version)
        to_record = self.family.get_version(self.to_version)

        updated_from = VersionRecord(
            business_app=from_record.business_app,
            state_apps=from_record.state_apps,
            status="handed_off",
            handed_off_to=str(self.to_version),
            handed_off_from=from_record.handed_off_from,
        )
        updated_to = VersionRecord(
            business_app=to_record.business_app,
            state_apps=to_record.state_apps,
            status="active",
            handed_off_to=to_record.handed_off_to,
            handed_off_from=str(self.from_version),
        )
        self.family.versions[self.from_version] = updated_from
        self.family.versions[self.to_version] = updated_to
        self.family.current_version = self.to_version
        registry.save_family(self.family)
