"""Network configuration for a deployment environment."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from linest.errors import ConfigError


@dataclass(frozen=True)
class NetworkConfig:
    """Configuration for deploying to a specific environment."""

    env: str
    operator: Any
    query_service_url: str
    wallet_dir: str
    wallet_services: dict[str, str]

    @classmethod
    def default_base_dir(cls) -> Path:
        """Return the default base directory for linest configuration."""
        home = Path.home()
        return home / ".config" / "micromeme"

    @classmethod
    def load(cls, env: str, base_dir: Path | None = None) -> "NetworkConfig":
        """Load network configuration for the given environment."""
        base = base_dir or cls.default_base_dir()
        config_path = base / "networks" / env / "config.json"

        if not config_path.exists():
            raise ConfigError(f"Network config not found: {config_path}")

        with config_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return cls._from_dict(env, data)

    @classmethod
    def _from_dict(cls, env: str, data: dict[str, Any]) -> "NetworkConfig":
        """Validate and create a NetworkConfig from a dictionary."""
        required = {"operator", "query_service_url", "wallet_dir", "wallet_services"}
        missing = required - set(data.keys())
        if missing:
            raise ConfigError(f"Missing network config keys: {missing}")

        wallet_dir = os.path.expanduser(data["wallet_dir"])
        wallet_services = {
            name: url for name, url in data.get("wallet_services", {}).items()
        }

        return cls(
            env=env,
            operator=data["operator"],
            query_service_url=data["query_service_url"],
            wallet_dir=wallet_dir,
            wallet_services=wallet_services,
        )

    def wallet_service_url(self, app_name: str) -> str:
        """Return the wallet service URL for the given app family."""
        if app_name not in self.wallet_services:
            raise ConfigError(f"No wallet service URL configured for {app_name}")
        return self.wallet_services[app_name]

    def deployments_dir(self, base_dir: Path | None = None) -> Path:
        """Return the deployments directory for this environment."""
        base = base_dir or self.default_base_dir()
        return base / "deployments" / self.env
