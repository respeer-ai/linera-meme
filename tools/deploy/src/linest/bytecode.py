"""Bytecode hashing and path utilities."""

import hashlib
from pathlib import Path


def compute_hash(bytecode_path: str) -> str:
    """Compute the SHA256 hash of a bytecode file."""
    path = Path(bytecode_path)
    if not path.exists():
        raise FileNotFoundError(f"Bytecode file not found: {bytecode_path}")

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return f"sha256:{digest}"
