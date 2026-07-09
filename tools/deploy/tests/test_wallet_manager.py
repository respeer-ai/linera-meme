"""Tests for idempotent wallet creation."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from linest.client.linera_client import LineraClient
from linest.client.wallet_manager import WalletManager


@pytest.fixture
def linera_client() -> MagicMock:
    return MagicMock(spec=LineraClient)


def test_ensure_wallets_creates_missing_wallets(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
    manager = WalletManager(
        wallet_dir=tmp_path,
        app_name="ams",
        faucet_url="https://faucet.example.com",
        linera_client=linera_client,
    )

    manager.ensure_wallets()

    assert linera_client.init_wallet.call_count == 2
    assert linera_client.request_chain.call_count == 1


def test_ensure_wallets_skips_existing_wallets(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
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
    )

    manager.ensure_wallets()

    linera_client.init_wallet.assert_not_called()
    linera_client.request_chain.assert_not_called()


def test_ensure_wallets_creates_only_missing_wallet(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
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


def test_ensure_wallets_respects_owner_count(
    linera_client: MagicMock,
    tmp_path: Path,
) -> None:
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
