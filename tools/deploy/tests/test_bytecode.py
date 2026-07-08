"""Tests for bytecode hashing utilities."""

from pathlib import Path

import pytest

from linest.bytecode import compute_hash


def test_compute_hash_returns_sha256_digest(tmp_path: Path) -> None:
    path = tmp_path / "contract.wasm"
    path.write_bytes(b"hello")

    digest = compute_hash(str(path))

    import hashlib

    expected = f"sha256:{hashlib.sha256(b'hello').hexdigest()}"
    assert digest == expected


def test_compute_hash_raises_when_file_missing(tmp_path: Path) -> None:
    missing = tmp_path / "missing.wasm"
    with pytest.raises(FileNotFoundError):
        compute_hash(str(missing))
