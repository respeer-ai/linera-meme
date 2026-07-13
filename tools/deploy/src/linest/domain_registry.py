"""Global registry for domain-relevant application entries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from linest.persistence import atomic_json_write


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
    ) -> None:
        """Register or update an app entry."""
        data = self.load()
        data[name] = {
            "chain_id": chain_id,
            "application_id": application_id,
        }
        atomic_json_write(self.path, data)

