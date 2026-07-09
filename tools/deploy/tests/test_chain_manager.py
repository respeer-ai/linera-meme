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
    client.query_balance.return_value = 100.0
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


def test_create_chain_tops_up_from_funder_pool_when_low(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    balances = {"default-chain": 19.5}

    def fake_query_balance(wallet_path, keystore_path, storage_path, chain_id):
        return balances.get(chain_id, 0.0)

    def fake_transfer(
        wallet_path, keystore_path, storage_path, from_chain, to_chain, amount
    ):
        if to_chain in balances:
            balances[to_chain] += float(amount)

    linera_client.query_balance.side_effect = fake_query_balance
    linera_client.transfer.side_effect = fake_transfer

    funder_dir = tmp_path / "funder" / "local" / "chains" / "0"
    funder_dir.mkdir(parents=True)
    (funder_dir / "wallet.json").write_text("{}")
    (funder_dir / "keystore.json").write_text("{}")

    family = AppFamily.create("ams", "local")
    manager = MultiOwnerChainManager(
        wallet_dir=tmp_path / "wallets",
        app_name="ams",
        linera_client=linera_client,
        base_dir=tmp_path,
        env="local",
        faucet_url="http://faucet",
    )

    manager.ensure_chain(
        family=family,
        creator_owner="owner-c",
        owners=["owner-0"],
    )

    linera_client.transfer.assert_called_once()



