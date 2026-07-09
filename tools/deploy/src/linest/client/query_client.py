"""HTTP GraphQL client for querying chain state."""

from typing import Any

import requests

from linest.errors import DeploymentError


class QueryClient:
    """Client for executing GraphQL queries and mutations against a Linera service."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def query(
        self,
        chain_id: str,
        application_id: str,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a GraphQL query against an application service."""
        url = f"{self.base_url}/chains/{chain_id}/applications/{application_id}"
        payload = {
            "query": query,
            "variables": variables or {},
        }
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        if "errors" in data:
            raise DeploymentError(f"GraphQL error: {data['errors']}")

        return data.get("data", {})

    def query_latest_state_version(
        self, chain_id: str, application_id: str
    ) -> int:
        """Return the latest registered state version from a business app."""
        data = self.query(chain_id, application_id, "{ latestStateVersion }")
        return data["latestStateVersion"]

    def query_state_applications(
        self, chain_id: str, application_id: str
    ) -> list[dict[str, Any]]:
        """Return the list of registered state applications from a business app."""
        data = self.query(
            chain_id,
            application_id,
            "{ stateApplications { version applicationId } }",
        )
        return data["stateApplications"]

    def query_business_application_id(
        self, chain_id: str, application_id: str
    ) -> str | None:
        """Return the business application ID stored in a state app."""
        data = self.query(chain_id, application_id, "{ businessApplicationId }")
        return data.get("businessApplicationId")

    def mutation_append_state(
        self,
        chain_id: str,
        application_id: str,
        state_application_id: str,
    ) -> bool:
        """Schedule an AppendState operation on a business app."""
        query = (
            f'mutation {{ appendState(stateApplicationId: "{state_application_id}") }}'
        )
        data = self.query(chain_id, application_id, query)
        return bool(data.get("appendState"))

    def mutation_handoff(
        self,
        chain_id: str,
        application_id: str,
        new_business_application_id: str,
    ) -> bool:
        """Schedule a Handoff operation on a business app."""
        query = (
            f'mutation {{ handoff(newBusinessApplicationId: "{new_business_application_id}") }}'
        )
        data = self.query(chain_id, application_id, query)
        return bool(data.get("handoff"))

    def import_chain(
        self,
        owner: str,
        chain_id: str,
    ) -> bool:
        """Import a chain into the query service wallet."""
        query = (
            "mutation ImportChain($owner: AccountOwner!, $chainId: ChainId!) "
            "{ importChain(owner: $owner, chainId: $chainId) }"
        )
        payload = {
            "query": query,
            "variables": {"owner": owner, "chainId": chain_id},
        }
        response = requests.post(self.base_url, json=payload, timeout=30)
        response.raise_for_status()

        data = response.json()
        if "errors" in data:
            raise DeploymentError(f"GraphQL error: {data['errors']}")

        return bool(data.get("data", {}).get("importChain"))
