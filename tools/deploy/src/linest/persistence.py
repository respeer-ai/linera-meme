"""Atomic file persistence utilities."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


def atomic_json_write(path: Path, data: dict[str, Any]) -> None:
    """Write JSON data atomically with a temporary backup.

    The existing file (if any) is copied to ``<path>.bak`` before the new
    content is written to ``<path>.tmp`` and renamed into place.
    """
    backup_path = path.with_suffix(path.suffix + ".bak")
    temp_path = path.with_suffix(path.suffix + ".tmp")

    if path.exists():
        shutil.copy2(path, backup_path)

    with temp_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")

    temp_path.replace(path)
