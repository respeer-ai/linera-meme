"""Tests for domain registration and generation."""

from pathlib import Path

import pytest

from linest.command.domain_command import DomainCommand
from linest.domain_registry import DomainRegistry
from linest.models.app_family import AppFamily
from linest.models.business_app import BusinessAppDeployment
from linest.registry import DeploymentRegistry


@pytest.fixture
def domain_registry(tmp_path: Path) -> DomainRegistry:
    return DomainRegistry(tmp_path / "domain.json")


@pytest.fixture
def deployment_registry(tmp_path: Path) -> DeploymentRegistry:
    return DeploymentRegistry(tmp_path / "deployments" / "local")


def test_register_and_generate(
    domain_registry: DomainRegistry,
    deployment_registry: DeploymentRegistry,
    tmp_path: Path,
) -> None:
    command = DomainCommand(domain_registry, deployment_registry)
    command.register("blob-gateway", "chain-bg", "app-bg")

    output = tmp_path / "domain.ts"
    command.generate(cluster="testnet-conway", output_path=output)

    content = output.read_text()
    assert "SUB_DOMAIN = 'testnet-conway.'" in content
    assert "BLOB_GATEWAY_CHAIN_ID = 'chain-bg'" in content
    assert "BLOB_GATEWAY_APPLICATION_ID = 'app-bg'" in content


def test_generate_includes_linest_managed_app(
    domain_registry: DomainRegistry,
    deployment_registry: DeploymentRegistry,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    business = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module",
        application_id="app-ams",
        creator_chain_id="chain-ams",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    family.add_version(1, "ams-v1", [], status="active")
    family.current_version = 1
    deployment_registry.save_deployment(business)
    deployment_registry.save_family(family)

    command = DomainCommand(domain_registry, deployment_registry)
    output = tmp_path / "domain.ts"
    command.generate(cluster="local", output_path=output)

    content = output.read_text()
    assert "AMS_CHAIN_ID = 'chain-ams'" in content
    assert "AMS_APPLICATION_ID = 'app-ams'" in content


def test_manual_entry_overrides_linest_app(
    domain_registry: DomainRegistry,
    deployment_registry: DeploymentRegistry,
    tmp_path: Path,
) -> None:
    family = AppFamily.create("ams", "local")
    business = BusinessAppDeployment.create(
        name="ams-v1",
        version=1,
        network="local",
        module_id="module",
        application_id="app-ams",
        creator_chain_id="chain-ams",
        contract_bytecode_path="/tmp/c.wasm",
        service_bytecode_path="/tmp/s.wasm",
        contract_bytecode_hash="sha256:a",
        service_bytecode_hash="sha256:b",
    )
    family.add_version(1, "ams-v1", [], status="active")
    family.current_version = 1
    deployment_registry.save_deployment(business)
    deployment_registry.save_family(family)

    command = DomainCommand(domain_registry, deployment_registry)
    command.register("ams", "manual-chain", "manual-app")
    output = tmp_path / "domain.ts"
    command.generate(cluster="local", output_path=output)

    content = output.read_text()
    assert "AMS_CHAIN_ID = 'manual-chain'" in content
    assert "AMS_APPLICATION_ID = 'manual-app'" in content
