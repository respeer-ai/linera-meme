"""Read application version from crate Cargo.toml files."""

from __future__ import annotations

import re
from pathlib import Path

from linest.errors import LinestError


def _read_cargo_version(cargo_path: Path) -> int:
    """Read the semver version from a Cargo.toml and return it as an integer.

    The semver version ``major.minor.patch`` is mapped to
    ``major * 1_000_000 + minor * 1_000 + patch``.
    """
    if not cargo_path.exists():
        raise LinestError(f"Cargo.toml not found: {cargo_path}")

    content = cargo_path.read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"(\d+)\.(\d+)\.(\d+)"', content, re.MULTILINE)
    if not match:
        raise LinestError(f"Could not find semver version in {cargo_path}")

    major, minor, patch = (int(group) for group in match.groups())
    return major * 1_000_000 + minor * 1_000 + patch


def read_crate_version(repo_dir: Path, app_name: str) -> int:
    """Return the integer version for a business app family from its Cargo.toml.

    The convention is ``<repo_dir>/<app_name>/app/Cargo.toml``.
    """
    return _read_cargo_version(repo_dir / app_name / "app" / "Cargo.toml")


def read_state_crate_version(repo_dir: Path, app_name: str) -> int:
    """Return the integer version for a state app family from its Cargo.toml.

    The convention is ``<repo_dir>/<app_name>/state/Cargo.toml``.
    """
    return _read_cargo_version(repo_dir / app_name / "state" / "Cargo.toml")
