"""Business application deployment model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from linest.models.deployment import Deployment


@dataclass(frozen=True)
class BusinessAppDeployment(Deployment):
    """A deployed business application."""

    state_apps: list[str]

    def __post_init__(self) -> None:
        if self.app_type != "business":
            raise ValueError(
                f"BusinessAppDeployment app_type must be 'business', got {self.app_type}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the business app deployment to a dictionary."""
        data = super().to_dict()
        data["state_apps"] = list(self.state_apps)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BusinessAppDeployment":
        """Deserialize a business app deployment from a dictionary."""
        base = Deployment.from_dict(data)
        return cls(
            name=base.name,
            app_type=base.app_type,
            version=base.version,
            network=base.network,
            module_id=base.module_id,
            application_id=base.application_id,
            creator_chain_id=base.creator_chain_id,
            contract_bytecode_path=base.contract_bytecode_path,
            service_bytecode_path=base.service_bytecode_path,
            contract_bytecode_hash=base.contract_bytecode_hash,
            service_bytecode_hash=base.service_bytecode_hash,
            instantiation_argument=base.instantiation_argument,
            state_apps=list(data.get("state_apps", [])),
        )

    @classmethod
    def create(
        cls,
        name: str,
        version: int,
        network: str,
        module_id: str,
        application_id: str,
        creator_chain_id: str,
        contract_bytecode_path: str,
        service_bytecode_path: str,
        contract_bytecode_hash: str,
        service_bytecode_hash: str,
        instantiation_argument: dict[str, Any] | None = None,
        state_apps: list[str] | None = None,
    ) -> "BusinessAppDeployment":
        """Create a new business app deployment record."""
        return cls(
            name=name,
            app_type="business",
            version=version,
            network=network,
            module_id=module_id,
            application_id=application_id,
            creator_chain_id=creator_chain_id,
            contract_bytecode_path=contract_bytecode_path,
            service_bytecode_path=service_bytecode_path,
            contract_bytecode_hash=contract_bytecode_hash,
            service_bytecode_hash=service_bytecode_hash,
            instantiation_argument=instantiation_argument or {},
            state_apps=state_apps or [],
        )
