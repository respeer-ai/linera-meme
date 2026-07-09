"""Tests for AppFamily upgrade history model."""

import pytest

from linest.errors import RegistryError, UpgradeError
from linest.models.app_family import AppFamily


def test_create_family_starts_at_version_zero() -> None:
    family = AppFamily.create("ams", "local")
    assert family.current_version == 0
    assert family.versions == {}


def test_add_version_and_retrieve() -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")

    record = family.get_version(1)
    assert record.business_app == "ams-v1"
    assert record.state_apps == ["ams-state-v1"]
    assert record.status == "active"


def test_add_duplicate_version_raises() -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", [], status="active")

    with pytest.raises(RegistryError):
        family.add_version(1, "ams-v1", [], status="active")


def test_get_missing_version_raises() -> None:
    family = AppFamily.create("ams", "local")
    with pytest.raises(RegistryError):
        family.get_version(1)


def test_previous_version() -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", [], status="active")
    family.add_version(2, "ams-v2", [], status="active")

    assert family.previous_version(2) == 1
    assert family.previous_version(1) is None


def test_validate_first_version_ok() -> None:
    family = AppFamily.create("ams", "local")
    family.validate_upgrade_target(1)


def test_validate_upgrade_rejects_older_version() -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", [], status="active")
    family.current_version = 1

    with pytest.raises(UpgradeError, match="greater than current"):
        family.validate_upgrade_target(1)


def test_validate_upgrade_next_version_ok() -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", [], status="active")
    family.current_version = 1

    family.validate_upgrade_target(2)


def test_serialize_and_deserialize() -> None:
    family = AppFamily.create("ams", "local")
    family.add_version(1, "ams-v1", ["ams-state-v1"], status="active")
    family.current_version = 1

    data = family.to_dict()
    loaded = AppFamily.from_dict(data)

    assert loaded.name == "ams"
    assert loaded.current_version == 1
    assert loaded.versions[1].business_app == "ams-v1"
