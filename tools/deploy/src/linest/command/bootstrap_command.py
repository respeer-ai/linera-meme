"""Bootstrap shared wallets and services for a deployment environment."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from linest.client.linera_client import LineraClient
from linest.client.wallet_service import WalletService
from linest.config import NetworkConfig, WalletPaths
from linest.errors import ConfigError


class BootstrapCommand:
    """Create operator/query wallets and start their services."""

    def __init__(
        self,
        config: NetworkConfig,
        linera_client: LineraClient,
        base_dir: Path,
        env: str,
    ) -> None:
        self.config = config
        self.linera_client = linera_client
        self.base_dir = base_dir
        self.env = env

    def bootstrap(
        self,
        faucet_url: str,
        operator_wallet_dir: Path,
        query_wallet_dir: Path,
        operator_service_port: int,
        query_service_port: int,
    ) -> None:
        """Ensure shared wallets exist and start their services."""
        operator_paths = self._wallet_paths(operator_wallet_dir)
        query_paths = self._wallet_paths(query_wallet_dir)

        operator_owner = self._ensure_wallet(operator_paths, faucet_url)
        query_owner = self._ensure_wallet(query_paths, faucet_url)

        operator_service = WalletService(
            wallet_path=operator_paths.wallet,
            keystore_path=operator_paths.keystore,
            storage_path=operator_paths.storage,
            port=operator_service_port,
        )
        operator_service_url = operator_service.start()

        query_service = WalletService(
            wallet_path=query_paths.wallet,
            keystore_path=query_paths.keystore,
            storage_path=query_paths.storage,
            port=query_service_port,
            extra_env={
                "LINERA_LISTENER_AUTO_IMPORT_OWNED_CHILD_CHAINS_WITHOUT_KEY": "true",
            },
        )
        query_service_url = query_service.start()

        self._write_config(
            operator_owner=operator_owner,
            operator_paths=operator_paths,
            operator_service_url=operator_service_url,
            query_paths=query_paths,
            query_service_url=query_service_url,
        )

    def _ensure_wallet(
        self,
        paths: WalletPaths,
        faucet_url: str,
    ) -> str:
        """Create a wallet if missing and return its default owner."""
        if not paths.wallet.exists() or not paths.keystore.exists():
            self.linera_client.init_wallet(
                paths.wallet,
                paths.keystore,
                paths.storage,
                faucet_url,
            )
            self.linera_client.request_chain(
                paths.wallet,
                paths.keystore,
                paths.storage,
                faucet_url,
            )
        return self.linera_client.default_owner(
            paths.wallet,
            paths.keystore,
            paths.storage,
        )

    @staticmethod
    def _wallet_paths(wallet_dir: Path) -> WalletPaths:
        return WalletPaths(
            wallet=wallet_dir / "wallet.json",
            keystore=wallet_dir / "keystore.json",
            storage=f"rocksdb://{wallet_dir / 'client.db'}",
        )

    def _write_config(
        self,
        operator_owner: str,
        operator_paths: WalletPaths,
        operator_service_url: str,
        query_paths: WalletPaths,
        query_service_url: str,
    ) -> None:
        config_dir = self.base_dir / "networks" / self.env
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"

        data: dict[str, Any] = {
            "operator": operator_owner,
            "operator_wallet": {
                "wallet": str(operator_paths.wallet),
                "keystore": str(operator_paths.keystore),
                "storage": operator_paths.storage,
            },
            "operator_service_url": operator_service_url,
            "query_wallet": {
                "wallet": str(query_paths.wallet),
                "keystore": str(query_paths.keystore),
                "storage": query_paths.storage,
            },
            "query_service_url": query_service_url,
            "wallet_dir": self.config.wallet_dir,
            "wallet_services": {},
        }

        with config_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
