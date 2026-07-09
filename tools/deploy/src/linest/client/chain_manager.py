"""Idempotent multi-owner chain creation for an app family."""

from __future__ import annotations

from pathlib import Path

from linest.client.linera_client import LineraClient
from linest.errors import DeploymentError
from linest.models.app_family import AppFamily


class MultiOwnerChainManager:
    """Ensure the app family has a multi-owner chain and it is assigned to owners."""

    def __init__(
        self,
        wallet_dir: str | Path,
        app_name: str,
        linera_client: LineraClient,
    ) -> None:
        self.wallet_dir = Path(wallet_dir)
        self.app_name = app_name
        self.linera_client = linera_client

    def ensure_chain(
        self,
        family: AppFamily,
        creator_owner: str,
        owners: list[str],
    ) -> str:
        """Return the creator chain ID, creating it if necessary."""
        self._validate_owners(family, creator_owner, owners)

        if family.creator_chain_id is not None:
            return family.creator_chain_id

        chain_id = self._create_chain(creator_owner, owners)
        family.creator_chain_id = chain_id
        return chain_id

    def _validate_owners(
        self,
        family: AppFamily,
        creator_owner: str,
        owners: list[str],
    ) -> None:
        if family.creator_owner is None:
            family.creator_owner = creator_owner
        elif family.creator_owner != creator_owner:
            raise DeploymentError(
                f"Creator owner mismatch: expected {family.creator_owner}, "
                f"got {creator_owner}"
            )

        if not family.owners:
            family.owners = list(owners)
        elif family.owners != owners:
            raise DeploymentError(
                f"Owner list mismatch: expected {family.owners}, got {owners}"
            )

    def _create_chain(self, creator_owner: str, owners: list[str]) -> str:
        wallet_path, keystore_path, storage_path = self._creator_wallet_paths()
        default_chain = self.linera_client.default_chain_id_for(
            wallet_path, keystore_path, storage_path
        )
        chain_id = self.linera_client.open_multi_owner_chain(
            wallet_path=wallet_path,
            keystore_path=keystore_path,
            storage_path=storage_path,
            from_chain_id=default_chain,
            owners=[creator_owner, *owners],
        )
        self._assign_chain_to_owners(chain_id, [creator_owner, *owners])
        return chain_id

    def _assign_chain_to_owners(
        self,
        chain_id: str,
        owners: list[str],
    ) -> None:
        for index, owner in enumerate(owners):
            wallet_path, keystore_path, storage_path = self._owner_wallet_paths(
                "creator" if index == 0 else str(index - 1)
            )
            self.linera_client.assign_chain(
                wallet_path=wallet_path,
                keystore_path=keystore_path,
                storage_path=storage_path,
                owner=owner,
                chain_id=chain_id,
            )

    def _creator_wallet_paths(self) -> tuple[Path, Path, str]:
        return self._wallet_paths("creator")

    def _owner_wallet_paths(self, index: str) -> tuple[Path, Path, str]:
        return self._wallet_paths(index)

    def _wallet_paths(self, index: str) -> tuple[Path, Path, str]:
        wallet_path = self.wallet_dir / self.app_name / index / "wallet.json"
        keystore_path = self.wallet_dir / self.app_name / index / "keystore.json"
        storage_path = (
            f"rocksdb://{self.wallet_dir / self.app_name / index / 'client.db'}"
        )
        return wallet_path, keystore_path, storage_path
