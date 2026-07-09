"""Tests for crate version reading."""

from pathlib import Path

import pytest

from linest.errors import LinestError
from linest.version import read_crate_version


def test_read_crate_version_maps_semver_to_integer(tmp_path: Path) -> None:
    crate_dir = tmp_path / "ams" / "app"
    crate_dir.mkdir(parents=True)
    (crate_dir / "Cargo.toml").write_text(
        '[package]\nname = "ams-app"\nversion = "0.1.0"\n'
    )

    assert read_crate_version(tmp_path, "ams") == 1000


def test_read_crate_version_rejects_missing_cargo_toml(tmp_path: Path) -> None:
    with pytest.raises(LinestError, match="Cargo.toml not found"):
        read_crate_version(tmp_path, "ams")


def test_read_crate_version_rejects_invalid_version(tmp_path: Path) -> None:
    crate_dir = tmp_path / "ams" / "app"
    crate_dir.mkdir(parents=True)
    (crate_dir / "Cargo.toml").write_text(
        '[package]\nname = "ams-app"\nversion = "not-a-semver"\n'
    )

    with pytest.raises(LinestError, match="Could not find semver version"):
        read_crate_version(tmp_path, "ams")
