"""Tests for DeployCommand orchestration."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.command.deploy_command import DeployCommand
from linest.config import NetworkConfig
from linest.registry import DeploymentRegistry


@pytest.fixture
def registry(tmp_path: Path) -> DeploymentRegistry:
    return DeploymentRegistry(tmp_path)


@pytest.fixture
def config() -> NetworkConfig:
    return NetworkConfig(
        env="local",
        operator="operator1",
        query_service_url="http://query:8080",
        wallet_dir="/wallets",
        wallet_services={"ams": "http://ams-wallet:8080"},
    )


@pytest.fixture
def linera_client() -> MagicMock:
    client = MagicMock(spec=LineraClient)
    client.default_chain_id.return_value = "chain1"
    client.publish_module.return_value = "module-id"
    client.create_application.side_effect = ["app-biz", "app-state"]
    client.bcs_serialize_application_operation.return_value = "0xdeadbeef"
    client.submit_application_operation.return_value = None
    return client


@pytest.fixture
def query_client() -> MagicMock:
    return MagicMock(spec=QueryClient)


def _write_file(path: Path, content: bytes = b"wasm") -> str:
    path.write_bytes(content)
    return str(path)


@pytest.fixture
def repo_dir(tmp_path: Path) -> Path:
    """Create a temporary repository root with ABI source files."""
    abi_dir = tmp_path / "abi" / "src" / "ams"
    abi_dir.mkdir(parents=True)
    (abi_dir / "state_v1.rs").write_text("state v1 abi")
    return tmp_path


def test_deploy_command_first_deploy(
    registry: DeploymentRegistry,
    config: NetworkConfig,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
    repo_dir: Path,
) -> None:
    command = DeployCommand(config, registry, linera_client, query_client)
    contract = _write_file(tmp_path / "contract.wasm")
    service = _write_file(tmp_path / "service.wasm")
    state_contract = _write_file(tmp_path / "state_contract.wasm")
    state_service = _write_file(tmp_path / "state_service.wasm")

    query_client.query_state_applications.return_value = []

    command.deploy(
        name="ams",
        version=1,
        contract_bytecode=contract,
        service_bytecode=service,
        state_contract_bytecode=state_contract,
        state_service_bytecode=state_service,
        dry_run=False,
        repo_dir=repo_dir,
    )

    family = registry.load_family("ams")
    assert family.current_version == 1
    assert 1 in family.versions

    business = registry.load_business_app("ams-v1")
    assert business.application_id == "app-biz"

    state = registry.load_state_app("ams-state-v1")
    assert state.application_id == "app-state"

    assert linera_client.submit_application_operation.call_count == 1


def test_deploy_command_dry_run_does_not_execute(
    registry: DeploymentRegistry,
    config: NetworkConfig,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
    repo_dir: Path,
) -> None:
    command = DeployCommand(config, registry, linera_client, query_client)
    contract = _write_file(tmp_path / "contract.wasm")
    service = _write_file(tmp_path / "service.wasm")
    state_contract = _write_file(tmp_path / "state_contract.wasm")
    state_service = _write_file(tmp_path / "state_service.wasm")

    command.deploy(
        name="ams",
        version=1,
        contract_bytecode=contract,
        service_bytecode=service,
        state_contract_bytecode=state_contract,
        state_service_bytecode=state_service,
        dry_run=True,
        repo_dir=repo_dir,
    )

    linera_client.publish_module.assert_not_called()
    linera_client.create_application.assert_not_called()
    linera_client.submit_application_operation.assert_not_called()

    family = registry.load_family("ams")
    assert family.current_version == 0
