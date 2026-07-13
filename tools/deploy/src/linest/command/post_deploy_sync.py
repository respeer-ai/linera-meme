"""Post-deployment synchronization for an app family."""

from __future__ import annotations

from pathlib import Path

from linest.client.linera_client import LineraClient
from linest.client.query_client import QueryClient
from linest.client.wallet_layout import AppWalletLayout
from linest.config import NetworkConfig, WalletPaths
from linest.errors import LineraCliError
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

        layout = AppWalletLayout(
            wallet_dir=wallet_dir, app_name=family.name
        )

        self._process_owner_inboxes(layout, owner_count)
        self._import_to_query_service(layout, chain_id)
        self._set_single_leader(layout, chain_id, owner_count)

    def _process_owner_inboxes(
        self,
        layout: AppWalletLayout,
        owner_count: int,
    ) -> None:
        self._process_inbox(layout.creator())
        for index in range(owner_count):
            self._process_inbox(layout.owner(index))

    def _process_inbox(self, paths: WalletPaths) -> None:
        self.linera_client.process_inbox(
            paths.wallet, paths.keystore, paths.storage
        )

    def _import_to_query_service(
        self,
        layout: AppWalletLayout,
        chain_id: str,
    ) -> None:
        if self.config.query_wallet is None:
            return

        existing_chain_ids = self.linera_client.wallet_chain_ids(
            self.config.query_wallet.wallet,
            self.config.query_wallet.keystore,
            self.config.query_wallet.storage,
        )
        if chain_id in existing_chain_ids:
            print(
                f"[post-deploy-sync] chain {chain_id} already imported to query service"
            )
            return

        query_owner = self._default_owner(layout.creator())
        self.query_client.import_chain(owner=query_owner, chain_id=chain_id)

    def _set_single_leader(
        self,
        layout: AppWalletLayout,
        chain_id: str,
        owner_count: int,
    ) -> None:
        owners: dict[str, int] = {}
        creator_owner = self._default_owner(layout.creator())
        owners[creator_owner] = 100
        for index in range(owner_count):
            owner = self._default_owner(layout.owner(index))
            owners[owner] = 100

        operator_paths = layout.owner(0)
        if self._already_single_leader(operator_paths, chain_id, owners):
            print(
                f"[post-deploy-sync] chain {chain_id} already in single-leader mode"
            )
            return

        self.linera_client.change_ownership(
            operator_paths.wallet,
            operator_paths.keystore,
            operator_paths.storage,
            chain_id,
            owners,
            multi_leader_rounds=0,
        )

    def _already_single_leader(
        self,
        paths: WalletPaths,
        chain_id: str,
        expected_owners: dict[str, int],
    ) -> bool:
        """Check whether the chain is already configured for single leader."""
        try:
            ownership = self.linera_client.show_ownership(
                paths.wallet, paths.keystore, paths.storage, chain_id
            )
        except LineraCliError:
            return False

        multi_leader_rounds = ownership.get("multi_leader_rounds")
        if multi_leader_rounds != 0:
            return False

        actual_owners = ownership.get("owners", {})
        return actual_owners == expected_owners

    def _default_owner(self, paths: WalletPaths) -> str:
        return self.linera_client.default_owner(
            paths.wallet, paths.keystore, paths.storage
        )
