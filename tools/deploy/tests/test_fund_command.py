"""Tests for FundCommand."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from linest.client.linera_client import LineraClient
from linest.command.fund_command import FundCommand
from linest.config import NetworkConfig
from linest.errors import LinestError
from linest.registry import DeploymentRegistry


@pytest.fixture
def config(tmp_path: Path) -> NetworkConfig:
    return NetworkConfig(
        env="local",
        operator="0xoperator",
        query_service_url="http://query:8080",
        wallet_dir=str(tmp_path / "wallets"),
        wallet_services={},
    )


@pytest.fixture
def registry(tmp_path: Path) -> DeploymentRegistry:
    return DeploymentRegistry(tmp_path / "deployments")


@pytest.fixture
def linera_client() -> MagicMock:
    client = MagicMock(spec=LineraClient)
    client.default_chain_id_for.return_value = "source-chain"
    client.query_balance.return_value = 10.0
    return client


@pytest.fixture
def command(
    tmp_path: Path,
    config: NetworkConfig,
    registry: DeploymentRegistry,
    linera_client: MagicMock,
) -> FundCommand:
    return FundCommand(
        config=config,
        registry=registry,
        linera_client=linera_client,
        base_dir=tmp_path,
    )


def test_fund_chains_requires_exactly_one_source(command: FundCommand) -> None:
    with pytest.raises(LinestError, match="source-wallet-dir or --claim-from-faucet"):
        command.fund_chains(min_balance=100.0)

    with pytest.raises(LinestError, match="source-wallet-dir or --claim-from-faucet"):
        command.fund_chains(
            min_balance=100.0,
            source_wallet_dir=Path("/w"),
            faucet_url="http://faucet",
        )


def _create_source_wallet(wallet_dir: Path) -> None:
    wallet_dir.mkdir(parents=True, exist_ok=True)
    (wallet_dir / "wallet.json").write_text("{}")
    (wallet_dir / "keystore.json").write_text("{}")


def test_fund_chains_skips_when_no_targets(
    tmp_path: Path,
    command: FundCommand,
    linera_client: MagicMock,
) -> None:
    source_dir = tmp_path / "funder"
    _create_source_wallet(source_dir)

    command.fund_chains(min_balance=100.0, source_wallet_dir=source_dir)

    linera_client.query_balance.assert_not_called()


def test_fund_chains_transfers_for_underfunded_chain(
    tmp_path: Path,
    command: FundCommand,
    registry: DeploymentRegistry,
    linera_client: MagicMock,
) -> None:
    family = registry.load_family("ams")
    family.creator_chain_id = "ams-creator-chain"
    family.creator_chain_wallet_dir = str(tmp_path / "wallets" / "ams" / "creator")
    registry.save_family(family)

    balances = {"ams-creator-chain": 10.0}

    def fake_query_balance(wallet_path, keystore_path, storage_path, chain_id):
        return balances.get(chain_id, 0.0)

    def fake_transfer(
        wallet_path, keystore_path, storage_path, from_chain, to_chain, amount
    ):
        if to_chain in balances:
            balances[to_chain] += float(amount)

    linera_client.query_balance.side_effect = fake_query_balance
    linera_client.transfer.side_effect = fake_transfer

    source_dir = tmp_path / "funder"
    _create_source_wallet(source_dir)
    command.fund_chains(min_balance=100.0, source_wallet_dir=source_dir)

    linera_client.transfer.assert_called_once()
    args = linera_client.transfer.call_args[0]
    assert args[3] == "source-chain"
    assert args[4] == "ams-creator-chain"


def test_fund_chains_skips_when_balance_is_sufficient(
    tmp_path: Path,
    command: FundCommand,
    registry: DeploymentRegistry,
    linera_client: MagicMock,
) -> None:
    family = registry.load_family("ams")
    family.creator_chain_id = "ams-creator-chain"
    registry.save_family(family)

    linera_client.query_balance.return_value = 150.0

    source_dir = tmp_path / "funder"
    _create_source_wallet(source_dir)
    command.fund_chains(min_balance=100.0, source_wallet_dir=source_dir)

    linera_client.transfer.assert_not_called()


def test_fund_chains_claims_multiple_funders_when_needed(
    tmp_path: Path,
    command: FundCommand,
    registry: DeploymentRegistry,
    linera_client: MagicMock,
) -> None:
    family = registry.load_family("ams")
    family.creator_chain_id = "ams-creator-chain"
    family.creator_chain_wallet_dir = str(tmp_path / "wallets" / "ams" / "creator")
    registry.save_family(family)

    target_balance = 10.0
    funder_balances: dict[str, float] = {}

    def fake_init_wallet(wallet_path, keystore_path, storage_path, faucet_url):
        wallet_dir = Path(wallet_path).parent
        wallet_dir.mkdir(parents=True, exist_ok=True)
        Path(wallet_path).write_text("{}")
        Path(keystore_path).write_text("{}")
        index = wallet_dir.name
        funder_balances[f"funder-{index}"] = 50.0

    def fake_default_chain_id_for(wallet_path, keystore_path, storage_path):
        wallet_path_str = str(wallet_path)
        if "funder" in wallet_path_str:
            index = Path(wallet_path).parent.name
            return f"funder-{index}"
        return "ams-creator-chain"

    def fake_query_balance(wallet_path, keystore_path, storage_path, chain_id):
        nonlocal target_balance
        if chain_id == "ams-creator-chain":
            return target_balance
        return funder_balances.get(chain_id, 0.0)

    def fake_transfer(
        wallet_path, keystore_path, storage_path, from_chain, to_chain, amount
    ):
        nonlocal target_balance
        if to_chain == "ams-creator-chain":
            target_balance += float(amount)
        if from_chain in funder_balances:
            funder_balances[from_chain] -= float(amount)

    linera_client.init_wallet.side_effect = fake_init_wallet
    linera_client.default_chain_id_for.side_effect = fake_default_chain_id_for
    linera_client.query_balance.side_effect = fake_query_balance
    linera_client.transfer.side_effect = fake_transfer

    command.fund_chains(min_balance=100.0, faucet_url="http://faucet")

    assert target_balance >= 100.0
    assert linera_client.init_wallet.call_count == 2


def test_list_funders_returns_claimed_funders(
    tmp_path: Path,
    command: FundCommand,
    linera_client: MagicMock,
) -> None:
    funder_dir = tmp_path / "funder" / "local" / "chains" / "0"
    funder_dir.mkdir(parents=True)
    (funder_dir / "wallet.json").write_text("{}")
    (funder_dir / "keystore.json").write_text("{}")
    linera_client.default_chain_id_for.return_value = "funder-chain"
    linera_client.query_balance.return_value = 42.0

    funders = command.list_funders()

    assert len(funders) == 1
    assert funders[0]["chain_id"] == "funder-chain"
    assert funders[0]["balance"] == "42.0"


def test_clean_funders_removes_spent_wallets(
    tmp_path: Path,
    command: FundCommand,
    linera_client: MagicMock,
) -> None:
    spent_dir = tmp_path / "funder" / "local" / "chains" / "0"
    spent_dir.mkdir(parents=True)
    (spent_dir / "wallet.json").write_text("{}")
    (spent_dir / "keystore.json").write_text("{}")
    linera_client.query_balance.return_value = 0.0

    removed = command.clean_funders()

    assert removed == 1
    assert not spent_dir.exists()



