"""Edge-case tests for deployment steps."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.errors import DeploymentError, RegistryError
from linest.models.app_family import AppFamily
from linest.models.business_app import BusinessAppDeployment
from linest.models.state_app import StateAppDeployment
from linest.registry import DeploymentRegistry
from linest.steps.deploy_business_app_step import DeployBusinessAppStep
from linest.steps.deploy_state_app_step import DeployStateAppStep


@pytest.fixture
def registry(tmp_path: Path) -> DeploymentRegistry:
    return DeploymentRegistry(tmp_path)


@pytest.fixture
def linera_client() -> MagicMock:
    client = MagicMock(spec=LineraClient)
    client.default_chain_id.return_value = "chain1"
    client.publish_module.return_value = "module-new"
    client.create_application.return_value = "app-new"
    client.bcs_serialize_application_operation.return_value = "0xdeadbeef"
    client.submit_application_operation.return_value = None
    return client


@pytest.fixture
def query_client() -> MagicMock:
    return MagicMock(spec=QueryClient)


def _write_file(path: Path, content: bytes = b"wasm") -> str:
    path.write_bytes(content)
    return str(path)


def test_deploy_business_app_step_raises_on_different_bytecode(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    existing = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module-old",
        application_id="app-old",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:oldhash",
        service_bytecode_hash="sha256:oldhash",
    )
    family.add_version(1, "ams-v1", [], status="active")
    registry.save_deployment(existing)
    registry.save_family(family)

    contract = _write_file(tmp_path / "contract.wasm")
    service = _write_file(tmp_path / "service.wasm")

    step = DeployBusinessAppStep(
        family=family,
        version=1,
        contract_bytecode_path=contract,
        service_bytecode_path=service,
        instantiation_argument={},
    )

    with pytest.raises(DeploymentError, match="different bytecode"):
        step.execute(registry, linera_client, query_client)


def test_deploy_state_app_step_is_idempotent(
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
    step.execute(registry, linera_client, query_client)
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    assert "already deployed" in result.message
    assert linera_client.publish_module.call_count == 1


def test_deploy_state_app_step_raises_on_different_abi_hash(
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
    existing_state = StateAppDeployment.create(
        name="ams-state-v1",
        version=1,
        network="local",
        module_id="module-state",
        application_id="app-state",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/sc.wasm",
        service_bytecode_path="/tmp/ss.wasm",
        contract_bytecode_hash="sha256:old",
        service_bytecode_hash="sha256:old",
        business_application_id="app-biz",
        abi_source_hash="sha256:abi-old",
    )
    family.add_version(1, "ams-v1", [], status="active")
    registry.save_deployment(business)
    registry.save_deployment(existing_state)
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
        abi_source_hash="sha256:abi-new",
    )

    with pytest.raises(DeploymentError, match="different identity"):
        step.execute(registry, linera_client, query_client)


def test_deploy_state_app_step_raises_when_business_app_missing(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    contract = _write_file(tmp_path / "state_contract.wasm")
    service = _write_file(tmp_path / "state_service.wasm")

    step = DeployStateAppStep(
        family=family,
        version=1,
        contract_bytecode_path=contract,
        service_bytecode_path=service,
        business_app_version=1,
        operator="operator1",
    )

    with pytest.raises(RegistryError):
        step.execute(registry, linera_client, query_client)


def test_append_state_step_proceeds_when_chain_query_fails(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
) -> None:
    from linest.steps.append_state_step import AppendStateStep

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

    from linest.errors import DeploymentError

    query_client.query_state_applications.side_effect = DeploymentError(
        "network down"
    )

    step = AppendStateStep(family, 1, "ams-state-v1")
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    linera_client.submit_application_operation.assert_called_once()


def test_handoff_step_proceeds_when_chain_query_fails(
    registry: DeploymentRegistry,
    linera_client: MagicMock,
    query_client: MagicMock,
) -> None:
    from linest.steps.handoff_step import HandoffStep

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

    from linest.errors import DeploymentError

    query_client.query_business_application_id.side_effect = DeploymentError(
        "network down"
    )

    step = HandoffStep(family, 1, 2)
    result = step.execute(registry, linera_client, query_client)

    assert result.success
    linera_client.submit_application_operation.assert_called_once()
