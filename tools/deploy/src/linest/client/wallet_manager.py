"""Idempotent wallet creation for an app family."""

from __future__ import annotations

from pathlib import Path

from linest.client.linera_client import LineraClient


class WalletManager:
    """Ensure the wallets required by an app family exist."""

    def __init__(
        self,
        wallet_dir: str | Path,
        app_name: str,
        faucet_url: str,
        linera_client: LineraClient,
    ) -> None:
        self.wallet_dir = Path(wallet_dir)
        self.app_name = app_name
        self.faucet_url = faucet_url
        self.linera_client = linera_client

        self.publisher_wallet_path = (
            self.wallet_dir / app_name / "creator" / "wallet.json"
        )
        self.publisher_keystore_path = (
            self.wallet_dir / app_name / "creator" / "keystore.json"
        )
        self.publisher_storage_path = (
            f"rocksdb://{self.wallet_dir / app_name / 'creator' / 'client.db'}"
        )

        self.creator_wallet_path = self.wallet_dir / app_name / "0" / "wallet.json"
        self.creator_keystore_path = (
            self.wallet_dir / app_name / "0" / "keystore.json"
        )
        self.creator_storage_path = (
            f"rocksdb://{self.wallet_dir / app_name / '0' / 'client.db'}"
        )

    def ensure_wallets(self) -> None:
        """Create publisher and creator wallets when they are missing."""
        self._ensure_publisher_wallet()
        self._ensure_creator_wallet()

    def _ensure_publisher_wallet(self) -> None:
        if self._wallet_exists(
            self.publisher_wallet_path, self.publisher_keystore_path
        ):
            return
        self.linera_client.init_wallet(
            self.publisher_wallet_path,
            self.publisher_keystore_path,
            self.publisher_storage_path,
            self.faucet_url,
        )

    def _ensure_creator_wallet(self) -> None:
        if self._wallet_exists(self.creator_wallet_path, self.creator_keystore_path):
            return
        self.linera_client.init_wallet(
            self.creator_wallet_path,
            self.creator_keystore_path,
            self.creator_storage_path,
            self.faucet_url,
        )
        self.linera_client.request_chain(
            self.creator_wallet_path,
            self.creator_keystore_path,
            self.creator_storage_path,
            self.faucet_url,
        )

    @staticmethod
    def _wallet_exists(wallet_path: Path, keystore_path: Path) -> bool:
        return wallet_path.exists() and keystore_path.exists()
