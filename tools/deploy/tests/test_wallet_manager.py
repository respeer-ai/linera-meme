"""Tests for idempotent wallet creation."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from linest.client.linera_client import LineraClient
from linest.client.wallet_manager import WalletManager
from linest.errors import DeploymentError, LineraCliError


@pytest.fixture
def linera_client() -> MagicMock:
    return MagicMock(spec=LineraClient)


def test_ensure_wallets_creates_missing_wallets(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    linera_client.keygen.return_value = "0xowner"
    manager = WalletManager(
        wallet_dir=tmp_path,
        app_name="ams",
        faucet_url="https://faucet.example.com",
        linera_client=linera_client,
    )

    manager.ensure_wallets()

    assert linera_client.init_wallet.call_count == 2
    assert linera_client.request_chain.call_count == 1
    assert linera_client.keygen.call_count == 1


def test_ensure_wallets_reuses_owners_from_registry(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    linera_client.default_owner.return_value = "0xexisting_owner"
    wallet_dir = tmp_path / "ams"
    (wallet_dir / "creator").mkdir(parents=True)
    (wallet_dir / "0").mkdir(parents=True)
    (wallet_dir / "creator" / "wallet.json").write_text("{}")
    (wallet_dir / "creator" / "keystore.json").write_text("{}")
    (wallet_dir / "0" / "wallet.json").write_text("{}")
    (wallet_dir / "0" / "keystore.json").write_text("{}")

    manager = WalletManager(
        wallet_dir=tmp_path,
        app_name="ams",
        faucet_url="https://faucet.example.com",
        linera_client=linera_client,
        existing_owners=["0xexisting_owner"],
    )

    creator_owner, owners = manager.ensure_wallets()

    linera_client.init_wallet.assert_not_called()
    linera_client.request_chain.assert_not_called()
    linera_client.keygen.assert_not_called()
    assert linera_client.default_owner.call_count == 2
    assert owners == ["0xexisting_owner"]


def test_ensure_wallets_rejects_registry_wallet_mismatch(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    linera_client.default_owner.return_value = "0xwallet_owner"
    wallet_dir = tmp_path / "ams"
    (wallet_dir / "creator").mkdir(parents=True)
    (wallet_dir / "0").mkdir(parents=True)
    (wallet_dir / "creator" / "wallet.json").write_text("{}")
    (wallet_dir / "creator" / "keystore.json").write_text("{}")
    (wallet_dir / "0" / "wallet.json").write_text("{}")
    (wallet_dir / "0" / "keystore.json").write_text("{}")

    manager = WalletManager(
        wallet_dir=tmp_path,
        app_name="ams",
        faucet_url="https://faucet.example.com",
        linera_client=linera_client,
        existing_owners=["0xregistry_owner"],
    )

    with pytest.raises(DeploymentError):
        manager.ensure_wallets()

    linera_client.init_wallet.assert_not_called()
    linera_client.keygen.assert_not_called()


def test_ensure_wallets_rejects_missing_default_owner_when_registry_has_owner(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    linera_client.default_owner.side_effect = [
        "0xcreator_owner",
        LineraCliError("Wallet has no default owner"),
    ]
    wallet_dir = tmp_path / "ams"
    (wallet_dir / "creator").mkdir(parents=True)
    (wallet_dir / "0").mkdir(parents=True)
    (wallet_dir / "creator" / "wallet.json").write_text("{}")
    (wallet_dir / "creator" / "keystore.json").write_text("{}")
    (wallet_dir / "0" / "wallet.json").write_text("{}")
    (wallet_dir / "0" / "keystore.json").write_text("{}")

    manager = WalletManager(
        wallet_dir=tmp_path,
        app_name="ams",
        faucet_url="https://faucet.example.com",
        linera_client=linera_client,
        existing_owners=["0xregistry_owner"],
    )

    with pytest.raises(DeploymentError):
        manager.ensure_wallets()

    linera_client.init_wallet.assert_not_called()
    linera_client.keygen.assert_not_called()


def test_ensure_wallets_creates_only_missing_wallet(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    linera_client.keygen.return_value = "0xowner"
    wallet_dir = tmp_path / "ams"
    (wallet_dir / "creator").mkdir(parents=True)
    (wallet_dir / "creator" / "wallet.json").write_text("{}")
    (wallet_dir / "creator" / "keystore.json").write_text("{}")

    manager = WalletManager(
        wallet_dir=tmp_path,
        app_name="ams",
        faucet_url="https://faucet.example.com",
        linera_client=linera_client,
    )

    manager.ensure_wallets()

    assert linera_client.init_wallet.call_count == 1
    assert linera_client.request_chain.call_count == 0
    assert linera_client.keygen.call_count == 1


def test_ensure_wallets_respects_owner_count(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    linera_client.keygen.return_value = "0xowner"
    manager = WalletManager(
        wallet_dir=tmp_path,
        app_name="ams",
        faucet_url="https://faucet.example.com",
        linera_client=linera_client,
        owner_count=3,
    )

    manager.ensure_wallets()

    assert linera_client.init_wallet.call_count == 4  # creator + 3 owners
    assert linera_client.request_chain.call_count == 1  # only creator
    assert linera_client.keygen.call_count == 3  # one per owner


def test_ensure_wallets_reuses_multiple_owners_from_registry(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    linera_client.default_owner.side_effect = [
        "0xcreator_owner",
        "0xowner_0",
        "0xowner_1",
    ]
    wallet_dir = tmp_path / "ams"
    (wallet_dir / "creator").mkdir(parents=True)
    (wallet_dir / "0").mkdir(parents=True)
    (wallet_dir / "1").mkdir(parents=True)
    (wallet_dir / "creator" / "wallet.json").write_text("{}")
    (wallet_dir / "creator" / "keystore.json").write_text("{}")
    (wallet_dir / "0" / "wallet.json").write_text("{}")
    (wallet_dir / "0" / "keystore.json").write_text("{}")
    (wallet_dir / "1" / "wallet.json").write_text("{}")
    (wallet_dir / "1" / "keystore.json").write_text("{}")

    manager = WalletManager(
        wallet_dir=tmp_path,
        app_name="ams",
        faucet_url="https://faucet.example.com",
        linera_client=linera_client,
        owner_count=2,
        existing_owners=["0xowner_0", "0xowner_1"],
    )

    creator_owner, owners = manager.ensure_wallets()

    linera_client.init_wallet.assert_not_called()
    linera_client.request_chain.assert_not_called()
    linera_client.keygen.assert_not_called()
    assert linera_client.default_owner.call_count == 3
    assert creator_owner == "0xcreator_owner"
    assert owners == ["0xowner_0", "0xowner_1"]
