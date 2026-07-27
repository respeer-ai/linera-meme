"""Idempotent wallet creation for an app family."""

from __future__ import annotations

from pathlib import Path

from linest.client.linera_client import LineraClient
from linest.client.wallet_layout import AppWalletLayout
from linest.config import WalletPaths
from linest.errors import DeploymentError, LineraCliError


class WalletManager:
    """Ensure the wallets required by an app family exist and are valid."""

    def __init__(
        self,
        wallet_dir: str | Path,
        app_name: str,
        faucet_url: str,
        linera_client: LineraClient,
        owner_count: int = 1,
        existing_owners: list[str] | None = None,
    ) -> None:
        self.layout = AppWalletLayout(
            wallet_dir=Path(wallet_dir), app_name=app_name
        )
        self.faucet_url = faucet_url
        self.linera_client = linera_client
        self.owner_count = owner_count
        self.existing_owners = existing_owners or []

    def ensure_wallets(self) -> tuple[str, list[str]]:
        """Create or validate wallets and return (creator_owner, owner_addresses)."""
        creator_owner = self._ensure_publisher_wallet()
        owners: list[str] = []
        for index in range(self.owner_count):
            owners.append(self._ensure_owner_wallet(index))
        return creator_owner, owners

    def _ensure_publisher_wallet(self) -> str:
        paths = self.layout.creator()
        if not self._wallet_is_valid(paths):
            self.linera_client.init_wallet(
                paths.wallet, paths.keystore, paths.storage, self.faucet_url
            )
            self.linera_client.request_chain(
                paths.wallet, paths.keystore, paths.storage, self.faucet_url
            )
        return self.linera_client.default_owner(
            paths.wallet, paths.keystore, paths.storage
        )

    def _ensure_owner_wallet(self, index: int) -> str:
        """Ensure an owner wallet exists and return its owner public key.

        Owner wallets do not request their own chain from the faucet. Instead,
        they hold an unassigned keypair whose public key becomes one of the
        owners of the application's multi-owner chain. Once the chain is
        created and assigned to this wallet, ``linera wallet show`` reports
        that owner as the wallet's default owner.
        """
        paths = self.layout.owner(index)

        # If the registry already records an owner for this index, verify that
        # the wallet actually contains the same owner before reusing it.
        if index < len(self.existing_owners):
            registry_owner = self.existing_owners[index]
            try:
                wallet_owner = self.linera_client.default_owner(
                    paths.wallet, paths.keystore, paths.storage
                )
            except LineraCliError:
                # The wallet exists but has no default owner, which means the
                # multi-owner chain has not been assigned to it yet. Return the
                # expected owner so the caller can assign the chain later.
                return registry_owner
            if wallet_owner != registry_owner:
                raise DeploymentError(
                    f"Owner wallet {self.layout.app_name}/{index} mismatch: "
                    f"registry has {registry_owner}, wallet has {wallet_owner}"
                )
            return registry_owner

        # First deployment: ensure the wallet exists and create the unassigned
        # owner key that will be used to open the multi-owner chain.
        if not self._wallet_is_valid(paths):
            self.linera_client.init_wallet(
                paths.wallet, paths.keystore, paths.storage, self.faucet_url
            )
        return self.linera_client.keygen(paths.wallet, paths.keystore, paths.storage)

    def _wallet_is_valid(self, paths: WalletPaths) -> bool:
        if not paths.wallet.exists() or not paths.keystore.exists():
            return False
        try:
            self.linera_client.wallet_show(
                paths.wallet, paths.keystore, paths.storage
            )
        except LineraCliError:
            return False
        return True
