"""Global registry for domain-relevant application entries."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


class DomainRegistry:
    """Persistent store for chain/application IDs used to generate domain.ts."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def load(self) -> dict[str, dict[str, str]]:
        """Return the registered app entries."""
        if not self.path.exists():
            return {}
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def register(
        self,
        name: str,
        chain_id: str,
        application_id: str,
        wallet_dir: str | None = None,
    ) -> None:
        """Register or update an app entry."""
        data = self.load()
        entry: dict[str, str] = {
            "chain_id": chain_id,
            "application_id": application_id,
        }
        if wallet_dir is not None:
            entry["wallet_dir"] = wallet_dir
        data[name] = entry
        self._atomic_write(data)

    def _atomic_write(self, data: dict[str, Any]) -> None:
        """Write data atomically with a temporary backup."""
        backup_path = self.path.with_suffix(".json.bak")
        temp_path = self.path.with_suffix(".json.tmp")

        if self.path.exists():
            shutil.copy2(self.path, backup_path)

        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        temp_path.replace(self.path)
