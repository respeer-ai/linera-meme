"""Idempotent wallet creation for an app family."""

from __future__ import annotations

from pathlib import Path

from linest.client.linera_client import LineraClient
from linest.errors import LineraCliError


class WalletManager:
    """Ensure the wallets required by an app family exist and are valid."""

    def __init__(
        self,
        wallet_dir: str | Path,
        app_name: str,
        faucet_url: str,
        linera_client: LineraClient,
        owner_count: int = 1,
    ) -> None:
        self.wallet_dir = Path(wallet_dir)
        self.app_name = app_name
        self.faucet_url = faucet_url
        self.linera_client = linera_client
        self.owner_count = owner_count

    def ensure_wallets(self) -> tuple[str, list[str]]:
        """Create or validate wallets and return (creator_owner, owner_addresses)."""
        creator_owner = self._ensure_publisher_wallet()
        owners: list[str] = []
        for index in range(self.owner_count):
            owners.append(self._ensure_owner_wallet(index))
        return creator_owner, owners

    def _ensure_publisher_wallet(self) -> str:
        paths = self._wallet_paths("creator")
        if not self._wallet_is_valid(*paths):
            self.linera_client.init_wallet(*paths, self.faucet_url)
            self.linera_client.request_chain(*paths, self.faucet_url)
        return self.linera_client.default_owner(*paths)

    def _ensure_owner_wallet(self, index: int) -> str:
        paths = self._wallet_paths(str(index))
        if not self._wallet_is_valid(*paths):
            self.linera_client.init_wallet(*paths, self.faucet_url)
            # Owner wallets receive their chain from the external multi-owner chain
            # flow; requesting a default chain here would create an unneeded chain.
        return self.linera_client.default_owner(*paths)

    def _wallet_is_valid(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
    ) -> bool:
        if not wallet_path.exists() or not keystore_path.exists():
            return False
        try:
            self.linera_client.wallet_show(wallet_path, keystore_path, storage_path)
        except LineraCliError:
            return False
        return True

    def _wallet_paths(
        self,
        index: str,
    ) -> tuple[Path, Path, str]:
        wallet_path = self.wallet_dir / self.app_name / index / "wallet.json"
        keystore_path = self.wallet_dir / self.app_name / index / "keystore.json"
        storage_path = f"rocksdb://{self.wallet_dir / self.app_name / index / 'client.db'}"
        return wallet_path, keystore_path, storage_path
