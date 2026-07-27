"""Tests for QueryClient."""

from unittest.mock import MagicMock, patch

import pytest

from linest.client.query_client import QueryClient
from linest.errors import DeploymentError


@pytest.fixture
def client() -> QueryClient:
    return QueryClient("http://localhost:8080")


def test_query_posts_to_application_endpoint(client: QueryClient) -> None:
    with patch("linest.client.query_client.requests.post") as mock_post:
        mock_post.return_value = _response({"latestStateVersion": 1})

        data = client.query("chain1", "app1", "{ latestStateVersion }")

        assert data == {"latestStateVersion": 1}
        mock_post.assert_called_once_with(
            "http://localhost:8080/chains/chain1/applications/app1",
            json={"query": "{ latestStateVersion }", "variables": {}},
            timeout=30,
        )


def test_query_raises_on_graphql_errors(client: QueryClient) -> None:
    with patch("linest.client.query_client.requests.post") as mock_post:
        mock_post.return_value = _response(
            data=None, errors=[{"message": "Unknown field"}]
        )

        with pytest.raises(DeploymentError, match="GraphQL error"):
            client.query("chain1", "app1", "{ badField }")


def test_query_latest_state_version(client: QueryClient) -> None:
    with patch("linest.client.query_client.requests.post") as mock_post:
        mock_post.return_value = _response({"latestStateVersion": 3})

        assert client.query_latest_state_version("chain1", "app1") == 3


def test_query_state_applications(client: QueryClient) -> None:
    with patch("linest.client.query_client.requests.post") as mock_post:
        mock_post.return_value = _response(
            {
                "stateApplications": [
                    {"version": 1, "applicationId": "state1"},
                    {"version": 2, "applicationId": "state2"},
                ]
            }
        )

        apps = client.query_state_applications("chain1", "app1")

        assert apps == [
            {"version": 1, "applicationId": "state1"},
            {"version": 2, "applicationId": "state2"},
        ]


def test_query_business_application_id_returns_id(client: QueryClient) -> None:
    with patch("linest.client.query_client.requests.post") as mock_post:
        mock_post.return_value = _response({"businessApplicationId": "biz1"})

        assert client.query_business_application_id("chain1", "state1") == "biz1"


def test_query_business_application_id_returns_none(client: QueryClient) -> None:
    with patch("linest.client.query_client.requests.post") as mock_post:
        mock_post.return_value = _response({"businessApplicationId": None})

        assert client.query_business_application_id("chain1", "state1") is None


def test_mutation_append_state(client: QueryClient) -> None:
    with patch("linest.client.query_client.requests.post") as mock_post:
        mock_post.return_value = _response({"appendState": True})

        result = client.mutation_append_state("chain1", "app1", "state2")

        assert result is True
        mock_post.assert_called_once()
        sent_query = mock_post.call_args.kwargs["json"]["query"]
        assert 'appendState(stateApplicationId: "state2")' in sent_query


def test_mutation_handoff(client: QueryClient) -> None:
    with patch("linest.client.query_client.requests.post") as mock_post:
        mock_post.return_value = _response({"handoff": True})

        result = client.mutation_handoff("chain1", "app1", "newbiz1")

        assert result is True
        sent_query = mock_post.call_args.kwargs["json"]["query"]
        assert 'handoff(newBusinessApplicationId: "newbiz1")' in sent_query


def _response(data: dict | None, errors: list | None = None) -> MagicMock:
    response = MagicMock()
    response.raise_for_status = MagicMock()
    payload: dict = {"data": data or {}}
    if errors is not None:
        payload["errors"] = errors
    response.json.return_value = payload
    return response
