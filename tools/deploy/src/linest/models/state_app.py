"""Typed state application deployment model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from linest.models.deployment import Deployment


@dataclass(frozen=True)
class StateAppDeployment(Deployment):
    """A deployed typed state application."""

    business_application_id: str
    abi_source_hash: str | None = None

    def __post_init__(self) -> None:
        if self.app_type != "state":
            raise ValueError(
                f"StateAppDeployment app_type must be 'state', got {self.app_type}"
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize the state app deployment to a dictionary."""
        data = super().to_dict()
        data["business_application_id"] = self.business_application_id
        if self.abi_source_hash is not None:
            data["abi_source_hash"] = self.abi_source_hash
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StateAppDeployment":
        """Deserialize a state app deployment from a dictionary."""
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
            business_application_id=data["business_application_id"],
            abi_source_hash=data.get("abi_source_hash"),
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
        business_application_id: str,
        instantiation_argument: dict[str, Any] | None = None,
        abi_source_hash: str | None = None,
    ) -> "StateAppDeployment":
        """Create a new state app deployment record."""
        return cls(
            name=name,
            app_type="state",
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
            business_application_id=business_application_id,
            abi_source_hash=abi_source_hash,
        )
