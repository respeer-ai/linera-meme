"""Deployment registry persistence."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from linest.errors import RegistryError
from linest.models.app_family import AppFamily
from linest.models.business_app import BusinessAppDeployment
from linest.models.deployment import Deployment
from linest.models.state_app import StateAppDeployment


class DeploymentRegistry:
    """Persistent store for deployment records."""

    def __init__(self, deployments_dir: Path) -> None:
        self.deployments_dir = deployments_dir
        self.deployments_dir.mkdir(parents=True, exist_ok=True)

    def family_path(self, name: str) -> Path:
        """Return the registry path for an app family."""
        return self.deployments_dir / f"{name}.json"

    def deployment_path(self, name: str) -> Path:
        """Return the registry path for a concrete deployment."""
        return self.deployments_dir / f"{name}.json"

    def load_family(self, name: str) -> AppFamily:
        """Load an app family from the registry."""
        path = self.family_path(name)
        if not path.exists():
            env = self.deployments_dir.name
            return AppFamily.create(name=name, env=env)

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return AppFamily.from_dict(data)

    def save_family(self, family: AppFamily) -> None:
        """Save an app family to the registry."""
        path = self.family_path(family.name)
        self._atomic_write(path, family.to_dict())

    def load_deployment(self, name: str) -> Deployment:
        """Load a concrete deployment from the registry."""
        path = self.deployment_path(name)
        if not path.exists():
            raise RegistryError(f"Deployment not found: {name}")

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        app_type = data.get("app_type")
        if app_type == "business":
            return BusinessAppDeployment.from_dict(data)
        if app_type == "state":
            return StateAppDeployment.from_dict(data)
        raise RegistryError(f"Unknown app_type: {app_type}")

    def load_business_app(self, name: str) -> BusinessAppDeployment:
        """Load a business app deployment from the registry."""
        deployment = self.load_deployment(name)
        if not isinstance(deployment, BusinessAppDeployment):
            raise RegistryError(f"Deployment {name} is not a business app")
        return deployment

    def load_state_app(self, name: str) -> StateAppDeployment:
        """Load a state app deployment from the registry."""
        deployment = self.load_deployment(name)
        if not isinstance(deployment, StateAppDeployment):
            raise RegistryError(f"Deployment {name} is not a state app")
        return deployment

    def save_deployment(self, deployment: Deployment) -> None:
        """Save a concrete deployment to the registry."""
        path = self.deployment_path(deployment.name)
        self._atomic_write(path, deployment.to_dict())

    def list_deployments(self) -> list[str]:
        """Return the names of all deployments in the registry."""
        if not self.deployments_dir.exists():
            return []
        return [
            path.stem
            for path in self.deployments_dir.glob("*.json")
            if path.stem != ""
        ]

    def _atomic_write(self, path: Path, data: dict[str, Any]) -> None:
        """Write data atomically with a temporary backup."""
        backup_path = path.with_suffix(".json.bak")
        temp_path = path.with_suffix(".json.tmp")

        if path.exists():
            shutil.copy2(path, backup_path)

        with temp_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")

        temp_path.replace(path)
