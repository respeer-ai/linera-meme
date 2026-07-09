"""Tests for upgrade plan generation."""

from pathlib import Path

import pytest

from linest.errors import UpgradeError
from linest.models.app_family import AppFamily
from linest.plan.upgrade_plan import UpgradePlan
from linest.steps.append_state_step import AppendStateStep
from linest.steps.deploy_business_app_step import DeployBusinessAppStep
from linest.steps.deploy_state_app_step import DeployStateAppStep
from linest.steps.handoff_step import HandoffStep


@pytest.fixture
def repo_dir(tmp_path: Path) -> Path:
    """Create a temporary repository root with ABI source files."""
    abi_dir = tmp_path / "abi" / "src" / "ams"
    abi_dir.mkdir(parents=True)
    (abi_dir / "state_v1.rs").write_text("state v1 abi")
    (abi_dir / "state_v2.rs").write_text("state v2 abi")
    return tmp_path


def test_first_deploy_plan_requires_business_and_state_bytecode() -> None:
    family = AppFamily.create("ams", "local")
    with pytest.raises(UpgradeError):
        UpgradePlan(
            family=family,
            target_version=1,
            contract_bytecode_path=None,
            service_bytecode_path=None,
            state_contract_bytecode_path=None,
            state_service_bytecode_path=None,
            operator="operator1",
        )


def test_first_deploy_plan_has_three_steps(repo_dir: Path) -> None:
    family = AppFamily.create("ams", "local")
    plan = UpgradePlan(
        family=family,
        target_version=1,
        contract_bytecode_path="/tmp/ams_app_contract.wasm",
        service_bytecode_path="/tmp/ams_app_service.wasm",
        state_contract_bytecode_path="/tmp/ams_state_contract.wasm",
        state_service_bytecode_path="/tmp/ams_state_service.wasm",
        operator="operator1",
        repo_dir=repo_dir,
    )

    assert len(plan.steps) == 3
    assert isinstance(plan.steps[0], DeployBusinessAppStep)
    assert isinstance(plan.steps[1], DeployStateAppStep)
    assert isinstance(plan.steps[2], AppendStateStep)


def test_upgrade_allows_non_sequential_version(repo_dir: Path) -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    family.current_version = 1

    plan = UpgradePlan(
        family=family,
        target_version=3,
        contract_bytecode_path="/tmp/ams_app_contract.wasm",
        service_bytecode_path="/tmp/ams_app_service.wasm",
        state_contract_bytecode_path=None,
        state_service_bytecode_path=None,
        operator="operator1",
        repo_dir=repo_dir,
    )

    assert len(plan.steps) == 3
    assert isinstance(plan.steps[0], DeployBusinessAppStep)
    assert isinstance(plan.steps[1], AppendStateStep)
    assert isinstance(plan.steps[2], HandoffStep)


def test_same_state_upgrade_plan_has_three_steps(repo_dir: Path) -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    family.current_version = 1

    plan = UpgradePlan(
        family=family,
        target_version=2,
        contract_bytecode_path="/tmp/ams_app_contract.wasm",
        service_bytecode_path="/tmp/ams_app_service.wasm",
        state_contract_bytecode_path=None,
        state_service_bytecode_path=None,
        operator="operator1",
        repo_dir=repo_dir,
    )

    assert len(plan.steps) == 3
    assert isinstance(plan.steps[0], DeployBusinessAppStep)
    assert isinstance(plan.steps[1], AppendStateStep)
    assert isinstance(plan.steps[2], HandoffStep)


def test_appended_state_upgrade_plan_has_new_state_step(repo_dir: Path) -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    family.current_version = 1

    plan = UpgradePlan(
        family=family,
        target_version=2,
        contract_bytecode_path="/tmp/ams_app_contract.wasm",
        service_bytecode_path="/tmp/ams_app_service.wasm",
        state_contract_bytecode_path="/tmp/ams_state_v2_contract.wasm",
        state_service_bytecode_path="/tmp/ams_state_v2_service.wasm",
        operator="operator1",
        repo_dir=repo_dir,
    )

    assert len(plan.steps) == 5
    assert isinstance(plan.steps[0], DeployBusinessAppStep)
    assert isinstance(plan.steps[1], AppendStateStep)
    assert isinstance(plan.steps[2], DeployStateAppStep)
    assert isinstance(plan.steps[3], AppendStateStep)
    assert isinstance(plan.steps[4], HandoffStep)
