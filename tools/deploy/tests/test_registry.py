"""Tests for the deployment registry."""

import json
from pathlib import Path

import pytest

from linest.models.app_family import AppFamily
from linest.models.business_app import BusinessAppDeployment
from linest.models.state_app import StateAppDeployment
from linest.registry import DeploymentRegistry


@pytest.fixture
def registry(tmp_path: Path) -> DeploymentRegistry:
    return DeploymentRegistry(tmp_path)


def test_load_missing_family_returns_empty(registry: DeploymentRegistry) -> None:
    family = registry.load_family("ams")
    assert family.name == "ams"
    assert family.current_version == 0
    assert family.versions == {}


def test_save_and_load_family(registry: DeploymentRegistry) -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    family.current_version = 1
    registry.save_family(family)

    loaded = registry.load_family("ams")
    assert loaded.current_version == 1
    assert loaded.versions[1].business_app == "ams-v1"
    assert loaded.versions[1].state_apps == ["ams-state-v1"]


def test_save_and_load_business_app(registry: DeploymentRegistry) -> None:
    app = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module1",
        application_id="app1",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/contract.wasm",
        service_bytecode_path="/tmp/service.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    registry.save_deployment(app)

    loaded = registry.load_business_app("ams-v1")
    assert loaded.application_id == "app1"
    assert loaded.state_apps == []


def test_load_deployment_with_wrong_type_fails(registry: DeploymentRegistry) -> None:
    state_app = StateAppDeployment.create(
        name="ams-state-v1",
        version=1,
        network="local",
        module_id="module1",
        application_id="app1",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/contract.wasm",
        service_bytecode_path="/tmp/service.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
        business_application_id="app0",
    )
    registry.save_deployment(state_app)

    with pytest.raises(Exception):
        registry.load_business_app("ams-state-v1")


def test_atomic_write_creates_backup(registry: DeploymentRegistry) -> None:
    app = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module1",
        application_id="app1",
        creator_chain_id="chain1",
        contract_bytecode_path="/tmp/contract.wasm",
        service_bytecode_path="/tmp/service.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    registry.save_deployment(app)
    registry.save_deployment(app)

    assert (registry.deployments_dir / "ams-v1.json").exists()
    assert (registry.deployments_dir / "ams-v1.json.bak").exists()
