"""Tests for deployment step execution."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.models.app_family import AppFamily
from linest.models.business_app import BusinessAppDeployment
from linest.models.state_app import StateAppDeployment
from linest.registry import DeploymentRegistry
from linest.steps.append_state_step import AppendStateStep
from linest.steps.deploy_business_app_step import DeployBusinessAppStep
from linest.steps.deploy_state_app_step import DeployStateAppStep
from linest.steps.handoff_step import HandoffStep


@pytest.fixture
def registry(tmp_path: Path) -> DeploymentRegistry:
    return DeploymentRegistry(tmp_path)


@pytest.fixture
def linera_client() -> MagicMock:
    client = MagicMock(spec=LineraClient)
    client.wallet_url_for.return_value = "http://wallet:8080"
    client.default_chain_id.return_value = "chain1"
    client.publish_module.return_value = "module-new"
    client.create_application.return_value = "app-new"
    client.call_operation.return_value = {"appendState": True}
    return client


@pytest.fixture
def query_client() -> MagicMock:
    return MagicMock(spec=QueryClient)


def _write_file(path: Path, content: bytes = b"wasm") -> str:
    path.write_bytes(content)
    return str(path)


def test_deploy_business_app_step_creates_deployment(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    contract = _write_file(tmp_path / "contract.wasm")
    service = _write_file(tmp_path / "service.wasm")

    step = DeployBusinessAppStep(
        family=family,
        version=1,
        contract_bytecode_path=contract,
        service_bytecode_path=service,
        instantiation_argument={},
    )
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    linera_client.publish_module.assert_called_once_with(contract, service)
    linera_client.create_application.assert_called_once()

    loaded = registry.load_business_app("ams-v1")
    assert loaded.application_id == "app-new"
    assert family.current_version == 0  # current_version updated by DeployCommand


def test_deploy_business_app_step_is_idempotent(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    contract = _write_file(tmp_path / "contract.wasm")
    service = _write_file(tmp_path / "service.wasm")

    step = DeployBusinessAppStep(
        family=family,
        version=1,
        contract_bytecode_path=contract,
        service_bytecode_path=service,
        instantiation_argument={},
    )
    step.execute(registry, linera_client, query_client)
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    assert "already deployed" in result.message
    assert linera_client.publish_module.call_count == 1


def test_deploy_state_app_step_creates_deployment(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    business = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module-biz",
        application_id="app-biz",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    family.add_version(1, "ams-v1", [], status="active")
    registry.save_deployment(business)
    registry.save_family(family)

    contract = _write_file(tmp_path / "state_contract.wasm")
    service = _write_file(tmp_path / "state_service.wasm")

    step = DeployStateAppStep(
        family=family,
        version=1,
        contract_bytecode_path=contract,
        service_bytecode_path=service,
        business_app_version=1,
        operator="operator1",
        abi_source_hash="sha256:abi",
    )
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    loaded = registry.load_state_app("ams-state-v1")
    assert loaded.business_application_id == "app-biz"
    assert loaded.instantiation_argument["operator"] == {
        "chain_id": "chain1",
        "owner": "operator1",
    }
    assert loaded.abi_source_hash == "sha256:abi"


def test_deploy_state_app_step_is_idempotent_by_abi_hash(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    business = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module-biz",
        application_id="app-biz",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    state = StateAppDeployment.create(
        name="ams-state-v1",
        version=1,
        network="local",
        module_id="module-state",
        application_id="app-state",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/sc.wasm",
        service_bytecode_path="/tmp/ss.wasm",
        contract_bytecode_hash="sha256:c",
        service_bytecode_hash="sha256:d",
        business_application_id="app-biz",
        abi_source_hash="sha256:abi",
    )
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    registry.save_deployment(business)
    registry.save_deployment(state)
    registry.save_family(family)

    contract = _write_file(tmp_path / "state_contract.wasm")
    service = _write_file(tmp_path / "state_service.wasm")

    step = DeployStateAppStep(
        family=family,
        version=1,
        contract_bytecode_path=contract,
        service_bytecode_path=service,
        business_app_version=1,
        operator="operator1",
        abi_source_hash="sha256:abi",
    )
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    assert "already deployed" in result.message
    linera_client.publish_module.assert_not_called()


def test_deploy_state_app_step_rejects_different_abi_hash(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    business = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module-biz",
        application_id="app-biz",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    state = StateAppDeployment.create(
        name="ams-state-v1",
        version=1,
        network="local",
        module_id="module-state",
        application_id="app-state",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/sc.wasm",
        service_bytecode_path="/tmp/ss.wasm",
        contract_bytecode_hash="sha256:c",
        service_bytecode_hash="sha256:d",
        business_application_id="app-biz",
        abi_source_hash="sha256:abi-old",
    )
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    registry.save_deployment(business)
    registry.save_deployment(state)
    registry.save_family(family)

    contract = _write_file(tmp_path / "state_contract.wasm")
    service = _write_file(tmp_path / "state_service.wasm")

    from linest.errors import DeploymentError

    step = DeployStateAppStep(
        family=family,
        version=1,
        contract_bytecode_path=contract,
        service_bytecode_path=service,
        business_app_version=1,
        operator="operator1",
        abi_source_hash="sha256:abi-new",
    )
    with pytest.raises(DeploymentError, match="different identity"):
        step.execute(registry, linera_client, query_client)


def test_append_state_step_executes_mutation(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    business = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module-biz",
        application_id="app-biz",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    state = StateAppDeployment.create(
        name="ams-state-v1",
        version=1,
        network="local",
        module_id="module-state",
        application_id="app-state",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/sc.wasm",
        service_bytecode_path="/tmp/ss.wasm",
        contract_bytecode_hash="sha256:c",
        service_bytecode_hash="sha256:d",
        business_application_id="app-biz",
    )
    family.add_version(1, "ams-v1", [], status="active")
    registry.save_deployment(business)
    registry.save_deployment(state)
    registry.save_family(family)

    query_client.query_state_applications.return_value = []

    step = AppendStateStep(family, 1, "ams-state-v1")
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    linera_client.call_operation.assert_called_once()
    args = linera_client.call_operation.call_args.kwargs
    assert args["application_id"] == "app-biz"
    assert args["variables"]["stateApplicationId"] == "app-state"

    updated = registry.load_business_app("ams-v1")
    assert updated.state_apps == ["ams-state-v1"]


def test_append_state_step_skips_when_already_on_chain(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    business = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module-biz",
        application_id="app-biz",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    state = StateAppDeployment.create(
        name="ams-state-v1",
        version=1,
        network="local",
        module_id="module-state",
        application_id="app-state",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/sc.wasm",
        service_bytecode_path="/tmp/ss.wasm",
        contract_bytecode_hash="sha256:c",
        service_bytecode_hash="sha256:d",
        business_application_id="app-biz",
    )
    family.add_version(1, "ams-v1", [], status="active")
    registry.save_deployment(business)
    registry.save_deployment(state)
    registry.save_family(family)

    query_client.query_state_applications.return_value = [
        {"version": 1, "applicationId": "app-state"}
    ]

    step = AppendStateStep(family, 1, "ams-state-v1")
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    assert "already appended" in result.message
    linera_client.call_operation.assert_not_called()

    updated = registry.load_business_app("ams-v1")
    assert updated.state_apps == ["ams-state-v1"]


def test_handoff_step_executes_mutation(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
) -> None:
    family = AppFamily.create("ams", "local")
    from_app = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module-old",
        application_id="app-old",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
        state_apps=["ams-state-v1"],
    )
    to_app = BusinessAppDeployment.create(
        name="ams-v2",
        version=2,
        network="local",
        module_id="module-new",
        application_id="app-new",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    state = StateAppDeployment.create(
        name="ams-state-v1",
        version=1,
        network="local",
        module_id="module-state",
        application_id="app-state",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/sc.wasm",
        service_bytecode_path="/tmp/ss.wasm",
        contract_bytecode_hash="sha256:c",
        service_bytecode_hash="sha256:d",
        business_application_id="app-old",
    )
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    family.add_version(2, "ams-v2", [], status="deployed")
    registry.save_deployment(from_app)
    registry.save_deployment(to_app)
    registry.save_deployment(state)
    registry.save_family(family)

    query_client.query_business_application_id.return_value = "app-old"

    step = HandoffStep(family, 1, 2)
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    linera_client.call_operation.assert_called_once()
    args = linera_client.call_operation.call_args.kwargs
    assert args["application_id"] == "app-old"
    assert args["variables"]["newBusinessApplicationId"] == "app-new"

    assert family.current_version == 2
    assert family.versions[1].status == "handed_off"
    assert family.versions[2].status == "active"


def test_handoff_step_skips_when_already_on_chain(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
) -> None:
    family = AppFamily.create("ams", "local")
    from_app = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module-old",
        application_id="app-old",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
        state_apps=["ams-state-v1"],
    )
    to_app = BusinessAppDeployment.create(
        name="ams-v2",
        version=2,
        network="local",
        module_id="module-new",
        application_id="app-new",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    state = StateAppDeployment.create(
        name="ams-state-v1",
        version=1,
        network="local",
        module_id="module-state",
        application_id="app-state",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/sc.wasm",
        service_bytecode_path="/tmp/ss.wasm",
        contract_bytecode_hash="sha256:c",
        service_bytecode_hash="sha256:d",
        business_application_id="app-old",
    )
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    family.add_version(2, "ams-v2", [], status="deployed")
    registry.save_deployment(from_app)
    registry.save_deployment(to_app)
    registry.save_deployment(state)
    registry.save_family(family)

    query_client.query_business_application_id.return_value = "app-new"

    step = HandoffStep(family, 1, 2)
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    assert "already completed" in result.message
    linera_client.call_operation.assert_not_called()
    assert family.current_version == 2
