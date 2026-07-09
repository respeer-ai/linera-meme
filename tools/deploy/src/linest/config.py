"""Network configuration for a deployment environment."""

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from linest.errors import ConfigError


@dataclass(frozen=True)
class WalletPaths:
    """Paths to a single linera wallet."""

    wallet: Path
    keystore: Path
    storage: str

    @classmethod
    def from_dict(cls, data: dict[str, Any], base_dir: Path) -> "WalletPaths":
        """Build wallet paths from a config dictionary."""
        wallet = Path(os.path.expanduser(data["wallet"]))
        if not wallet.is_absolute():
            wallet = base_dir / wallet
        keystore = Path(os.path.expanduser(data["keystore"]))
        if not keystore.is_absolute():
            keystore = base_dir / keystore
        storage = data["storage"]
        return cls(wallet=wallet, keystore=keystore, storage=storage)

    @classmethod
    def from_wallet_dir(cls, wallet_dir: Path) -> "WalletPaths":
        """Build wallet paths from a wallet directory."""
        wallet_dir = wallet_dir.expanduser()
        return cls(
            wallet=wallet_dir / "wallet.json",
            keystore=wallet_dir / "keystore.json",
            storage=f"rocksdb://{wallet_dir / 'client.db'}",
        )


@dataclass(frozen=True)
class NetworkConfig:
    """Configuration for deploying to a specific environment."""

    env: str
    operator: Any
    query_service_url: str
    wallet_dir: str
    wallet_services: dict[str, str]
    operator_wallet: WalletPaths | None = None
    query_wallet: WalletPaths | None = None
    operator_service_url: str | None = None

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

        return cls._from_dict(env, data, base)

    @classmethod
    def _from_dict(
        cls, env: str, data: dict[str, Any], base_dir: Path
    ) -> "NetworkConfig":
        """Validate and create a NetworkConfig from a dictionary."""
        required = {"operator", "query_service_url", "wallet_dir", "wallet_services"}
        missing = required - set(data.keys())
        if missing:
            raise ConfigError(f"Missing network config keys: {missing}")

        wallet_dir = os.path.expanduser(data["wallet_dir"])
        wallet_services = {
            name: url for name, url in data.get("wallet_services", {}).items()
        }

        operator_wallet = None
        if "operator_wallet" in data:
            operator_wallet = WalletPaths.from_dict(
                data["operator_wallet"], base_dir
            )

        query_wallet = None
        if "query_wallet" in data:
            query_wallet = WalletPaths.from_dict(data["query_wallet"], base_dir)

        return cls(
            env=env,
            operator=data["operator"],
            query_service_url=data["query_service_url"],
            wallet_dir=wallet_dir,
            wallet_services=wallet_services,
            operator_wallet=operator_wallet,
            query_wallet=query_wallet,
            operator_service_url=data.get("operator_service_url"),
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
