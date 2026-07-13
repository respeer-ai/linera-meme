"""Post-deployment synchronization for an app family."""

from __future__ import annotations

from pathlib import Path

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.config import NetworkConfig
from linest.models.app_family import AppFamily


class PostDeploySync:
    """Synchronize a freshly deployed app with the query service and owners."""

    def __init__(
        self,
        config: NetworkConfig,
        linera_client: LineraClient,
        query_client: QueryClient,
    ) -> None:
        self.config = config
        self.linera_client = linera_client
        self.query_client = query_client

    def sync(
        self,
        family: AppFamily,
        wallet_dir: Path,
        owner_count: int,
    ) -> None:
        """Run all post-deploy synchronization steps."""
        chain_id = family.creator_chain_id
        if chain_id is None:
            return

        self._process_owner_inboxes(wallet_dir, family.name, owner_count)
        self._import_to_query_service(family, wallet_dir, owner_count, chain_id)
        self._set_single_leader(wallet_dir, family.name, chain_id, owner_count)

    def _process_owner_inboxes(
        self,
        wallet_dir: Path,
        app_name: str,
        owner_count: int,
    ) -> None:
        self._process_inbox(wallet_dir, app_name, "creator")
        for index in range(owner_count):
            self._process_inbox(wallet_dir, app_name, str(index))

    def _process_inbox(
        self,
        wallet_dir: Path,
        app_name: str,
        index: str,
    ) -> None:
        wallet_path, keystore_path, storage_path = self._wallet_paths(
            wallet_dir, app_name, index
        )
        self.linera_client.process_inbox(wallet_path, keystore_path, storage_path)

    def _import_to_query_service(
        self,
        family: AppFamily,
        wallet_dir: Path,
        owner_count: int,
        chain_id: str,
    ) -> None:
        if self.config.query_wallet is None:
            return
        if owner_count == 0:
            return
        query_owner = self._default_owner(wallet_dir, family.name, "0")
        self.query_client.import_chain(owner=query_owner, chain_id=chain_id)

    def _set_single_leader(
        self,
        wallet_dir: Path,
        app_name: str,
        chain_id: str,
        owner_count: int,
    ) -> None:
        owners: dict[str, int] = {}
        creator_owner = self._default_owner(wallet_dir, app_name, "creator")
        owners[creator_owner] = 100
        for index in range(owner_count):
            owner = self._default_owner(wallet_dir, app_name, str(index))
            owners[owner] = 100

        wallet_path, keystore_path, storage_path = self._wallet_paths(
            wallet_dir, app_name, "0"
        )
        self.linera_client.change_ownership(
            wallet_path,
            keystore_path,
            storage_path,
            chain_id,
            owners,
            multi_leader_rounds=0,
        )

    def _default_owner(
        self,
        wallet_dir: Path,
        app_name: str,
        index: str,
    ) -> str:
        wallet_path, keystore_path, storage_path = self._wallet_paths(
            wallet_dir, app_name, index
        )
        return self.linera_client.default_owner(
            wallet_path, keystore_path, storage_path
        )

    @staticmethod
    def _wallet_paths(
        wallet_dir: Path,
        app_name: str,
        index: str,
    ) -> tuple[Path, Path, str]:
        wallet_path = wallet_dir / app_name / index / "wallet.json"
        keystore_path = wallet_dir / app_name / index / "keystore.json"
        storage_path = f"rocksdb://{wallet_dir / app_name / index / 'client.db'}"
        return wallet_path, keystore_path, storage_path
