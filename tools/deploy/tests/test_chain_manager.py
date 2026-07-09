"""Tests for multi-owner chain creation."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from linest.client.chain_manager import MultiOwnerChainManager
from linest.client.linera_client import LineraClient
from linest.errors import DeploymentError
from linest.models.app_family import AppFamily


@pytest.fixture
def linera_client() -> MagicMock:
    client = MagicMock(spec=LineraClient)
    client.default_chain_id_for.return_value = "default-chain"
    client.open_multi_owner_chain.return_value = "new-chain"
    return client


def test_ensure_chain_creates_chain_when_missing(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    manager = MultiOwnerChainManager(
        wallet_dir=tmp_path,
        app_name="ams",
        linera_client=linera_client,
    )

    chain_id = manager.ensure_chain(
        family=family,
        creator_owner="owner-c",
        owners=["owner-0", "owner-1"],
    )

    assert chain_id == "new-chain"
    assert family.creator_chain_id == "new-chain"
    assert family.creator_owner == "owner-c"
    assert family.owners == ["owner-0", "owner-1"]
    linera_client.open_multi_owner_chain.assert_called_once()


def test_ensure_chain_returns_existing_chain(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    family.creator_owner = "owner-c"
    family.owners = ["owner-0", "owner-1"]
    family.creator_chain_id = "existing-chain"

    manager = MultiOwnerChainManager(
        wallet_dir=tmp_path,
        app_name="ams",
        linera_client=linera_client,
    )

    chain_id = manager.ensure_chain(
        family=family,
        creator_owner="owner-c",
        owners=["owner-0", "owner-1"],
    )

    assert chain_id == "existing-chain"
    linera_client.open_multi_owner_chain.assert_not_called()


def test_ensure_chain_rejects_owner_mismatch(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    family.creator_owner = "owner-c"
    family.owners = ["owner-0", "owner-1"]
    family.creator_chain_id = "existing-chain"

    manager = MultiOwnerChainManager(
        wallet_dir=tmp_path,
        app_name="ams",
        linera_client=linera_client,
    )

    with pytest.raises(DeploymentError, match="Owner list mismatch"):
        manager.ensure_chain(
            family=family,
            creator_owner="owner-c",
            owners=["owner-0", "owner-2"],
        )
