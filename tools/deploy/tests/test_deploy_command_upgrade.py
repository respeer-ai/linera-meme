"""Tests for DeployCommand upgrade scenarios and recovery."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.command.deploy_command import DeployCommand
from linest.config import NetworkConfig
from linest.models.app_family import AppFamily
from linest.models.business_app import BusinessAppDeployment
from linest.models.state_app import StateAppDeployment
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
    client.wallet_url_for.return_value = "http://ams-wallet:8080"
    client.default_chain_id.return_value = "chain1"
    client.publish_module.return_value = "module-v2"
    client.create_application.return_value = "app-biz-v2"
    client.call_operation.return_value = {"handoff": True}
    return client


@pytest.fixture
def query_client() -> MagicMock:
    return MagicMock(spec=QueryClient)


def _write_file(path: Path, content: bytes = b"wasm") -> str:
    path.write_bytes(content)
    return str(path)


def _seed_v1(registry: DeploymentRegistry) -> None:
    family = AppFamily.create("ams", "local")
    business = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module-v1",
        application_id="app-biz-v1",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
        state_apps=["ams-state-v1"],
    )
    state = StateAppDeployment.create(
        name="ams-state-v1",
        version=1,
        network="local",
        module_id="module-state-v1",
        application_id="app-state-v1",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/sc.wasm",
        service_bytecode_path="/tmp/ss.wasm",
        contract_bytecode_hash="sha256:c",
        service_bytecode_hash="sha256:d",
        business_application_id="app-biz-v1",
    )
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    family.current_version = 1
    registry.save_deployment(business)
    registry.save_deployment(state)
    registry.save_family(family)


def test_upgrade_v1_to_v2(
    registry: DeploymentRegistry,
    config: NetworkConfig,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    _seed_v1(registry)
    command = DeployCommand(config, registry, linera_client, query_client)
    contract = _write_file(tmp_path / "contract.wasm")
    service = _write_file(tmp_path / "service.wasm")

    query_client.query_state_applications.return_value = []
    query_client.query_business_application_id.return_value = "app-biz-v1"

    command.deploy(
        name="ams",
        version=2,
        contract_bytecode=contract,
        service_bytecode=service,
        state_contract_bytecode=None,
        state_service_bytecode=None,
        dry_run=False,
    )

    family = registry.load_family("ams")
    assert family.current_version == 2
    assert family.versions[2].status == "active"
    assert family.versions[1].status == "handed_off"

    assert linera_client.publish_module.call_count == 1
    assert linera_client.create_application.call_count == 1
    assert linera_client.call_operation.call_count == 2


def test_upgrade_recovers_after_append_state(
    registry: DeploymentRegistry,
    config: NetworkConfig,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    _seed_v1(registry)
    command = DeployCommand(config, registry, linera_client, query_client)
    contract = _write_file(tmp_path / "contract.wasm")
    service = _write_file(tmp_path / "service.wasm")

    # Chain already has the state app appended to v2 business app, but handoff not done.
    query_client.query_state_applications.return_value = [
        {"version": 1, "applicationId": "app-state-v1"}
    ]
    query_client.query_business_application_id.return_value = "app-biz-v1"

    command.deploy(
        name="ams",
        version=2,
        contract_bytecode=contract,
        service_bytecode=service,
        state_contract_bytecode=None,
        state_service_bytecode=None,
        dry_run=False,
    )

    family = registry.load_family("ams")
    assert family.current_version == 2
    assert family.versions[1].status == "handed_off"

    # One call for appendState (skipped) and one for handoff.
    assert linera_client.call_operation.call_count == 1
    args = linera_client.call_operation.call_args.kwargs
    assert "handoff" in args["mutation"]


def test_upgrade_recovers_after_handoff(
    registry: DeploymentRegistry,
    config: NetworkConfig,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    _seed_v1(registry)
    command = DeployCommand(config, registry, linera_client, query_client)
    contract = _write_file(tmp_path / "contract.wasm")
    service = _write_file(tmp_path / "service.wasm")

    # Chain already shows handoff completed.
    query_client.query_state_applications.return_value = [
        {"version": 1, "applicationId": "app-state-v1"}
    ]
    query_client.query_business_application_id.return_value = "app-biz-v2"

    command.deploy(
        name="ams",
        version=2,
        contract_bytecode=contract,
        service_bytecode=service,
        state_contract_bytecode=None,
        state_service_bytecode=None,
        dry_run=False,
    )

    family = registry.load_family("ams")
    assert family.current_version == 2
    assert family.versions[1].status == "handed_off"
    assert family.versions[2].status == "active"

    linera_client.call_operation.assert_not_called()


def test_upgrade_rejects_older_version(
    registry: DeploymentRegistry,
    config: NetworkConfig,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    _seed_v1(registry)
    command = DeployCommand(config, registry, linera_client, query_client)
    contract = _write_file(tmp_path / "contract.wasm")
    service = _write_file(tmp_path / "service.wasm")

    from linest.errors import UpgradeError

    with pytest.raises(UpgradeError):
        command.deploy(
            name="ams",
            version=1,
            contract_bytecode=contract,
            service_bytecode=service,
            state_contract_bytecode=None,
            state_service_bytecode=None,
            dry_run=False,
        )
