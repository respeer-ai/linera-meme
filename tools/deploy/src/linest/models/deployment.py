"""Base class for deployed applications."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Deployment:
    """A deployed Linera application."""

    name: str
    app_type: str
    version: int
    network: str
    module_id: str
    application_id: str
    creator_chain_id: str
    contract_bytecode_path: str
    service_bytecode_path: str
    contract_bytecode_hash: str
    service_bytecode_hash: str
    instantiation_argument: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Serialize the deployment to a dictionary."""
        return {
            "name": self.name,
            "app_type": self.app_type,
            "version": self.version,
            "network": self.network,
            "module_id": self.module_id,
            "application_id": self.application_id,
            "creator_chain_id": self.creator_chain_id,
            "contract_bytecode_path": self.contract_bytecode_path,
            "service_bytecode_path": self.service_bytecode_path,
            "contract_bytecode_hash": self.contract_bytecode_hash,
            "service_bytecode_hash": self.service_bytecode_hash,
            "instantiation_argument": self.instantiation_argument,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Deployment":
        """Deserialize a deployment from a dictionary."""
        return cls(
            name=data["name"],
            app_type=data["app_type"],
            version=data["version"],
            network=data["network"],
            module_id=data["module_id"],
            application_id=data["application_id"],
            creator_chain_id=data["creator_chain_id"],
            contract_bytecode_path=data["contract_bytecode_path"],
            service_bytecode_path=data["service_bytecode_path"],
            contract_bytecode_hash=data["contract_bytecode_hash"],
            service_bytecode_hash=data["service_bytecode_hash"],
            instantiation_argument=data.get("instantiation_argument", {}),
        )

    @property
    def registry_file_name(self) -> str:
        """Return the registry file name for this deployment."""
        return f"{self.name}.json"

    def registry_path(self, deployments_dir: Path) -> Path:
        """Return the full registry path for this deployment."""
        return deployments_dir / self.registry_file_name
