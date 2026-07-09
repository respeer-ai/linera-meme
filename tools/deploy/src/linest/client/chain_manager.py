"""Idempotent multi-owner chain creation for an app family."""

from __future__ import annotations

from pathlib import Path
from time import monotonic, sleep

from linest.client.funder_pool import FunderPool
from linest.client.linera_client import LineraClient
from linest.config import WalletPaths
from linest.errors import DeploymentError
from linest.models.app_family import AppFamily


class MultiOwnerChainManager:
    """Ensure the app family has a multi-owner chain and it is assigned to owners."""

    _CREATOR_CHAIN_TARGET_BALANCE: float = 25.0
    _TRANSFER_FEE_BUFFER: float = 0.1
    _FUNDING_COOLDOWN_SECONDS: float = 60.0
    _FUNDING_COOLDOWN_INTERVAL: float = 2.0

    def __init__(
        self,
        wallet_dir: str | Path,
        app_name: str,
        linera_client: LineraClient,
        base_dir: str | Path | None = None,
        env: str | None = None,
        faucet_url: str | None = None,
    ) -> None:
        self.wallet_dir = Path(wallet_dir)
        self.app_name = app_name
        self.linera_client = linera_client
        self.funder_pool: FunderPool | None = None
        if base_dir is not None and env is not None and faucet_url is not None:
            self.funder_pool = FunderPool(
                base_dir=Path(base_dir),
                env=env,
                faucet_url=faucet_url,
                linera_client=linera_client,
            )

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
        self._ensure_creator_chain_balance(
            wallet_path, keystore_path, storage_path, default_chain
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

    def _ensure_creator_chain_balance(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        chain_id: str,
    ) -> None:
        """Top up the creator chain from the funder pool before opening a chain."""
        print(f"[funder-check] funder_pool={'yes' if self.funder_pool else 'no'} chain={chain_id}")
        if self.funder_pool is None:
            return

        current_balance = self.linera_client.query_balance(
            wallet_path, keystore_path, storage_path, chain_id
        )
        print(f"[funder-check] current_balance={current_balance} target={self._CREATOR_CHAIN_TARGET_BALANCE}")
        if current_balance >= self._CREATOR_CHAIN_TARGET_BALANCE:
            print("[funder-check] balance sufficient, skipping")
            return

        amount = (
            self._CREATOR_CHAIN_TARGET_BALANCE
            - current_balance
            + self._TRANSFER_FEE_BUFFER
        )
        funder_chain_id = self.funder_pool.next_available_chain_id()
        print(f"[funder-check] funder_chain={funder_chain_id} transfer_amount={amount}")
        funder_dir = self.funder_pool.wallet_dir_for(funder_chain_id)
        funder_paths = WalletPaths.from_wallet_dir(funder_dir)
        self.linera_client.transfer(
            funder_paths.wallet,
            funder_paths.keystore,
            funder_paths.storage,
            funder_chain_id,
            chain_id,
            f"{amount:.10g}",
        )
        print("[funder-check] transfer complete")
        self._wait_for_balance(
            wallet_path, keystore_path, storage_path, chain_id
        )

    def _wait_for_balance(
        self,
        wallet_path: Path,
        keystore_path: Path,
        storage_path: str,
        chain_id: str,
    ) -> bool:
        """Wait for a funding transfer to land by polling inbox and balance."""
        print(
            f"[funder-check] waiting for balance on {chain_id} "
            f"to reach {self._CREATOR_CHAIN_TARGET_BALANCE}",
            flush=True,
        )
        deadline = monotonic() + self._FUNDING_COOLDOWN_SECONDS
        while monotonic() < deadline:
            self.linera_client.process_inbox(
                wallet_path, keystore_path, storage_path, chain_id
            )
            balance = self.linera_client.query_balance(
                wallet_path, keystore_path, storage_path, chain_id
            )
            print(
                f"[funder-check] chain {chain_id} balance {balance} "
                f"target {self._CREATOR_CHAIN_TARGET_BALANCE}",
                flush=True,
            )
            if balance >= self._CREATOR_CHAIN_TARGET_BALANCE:
                print(
                    f"[funder-check] balance {balance} landed on {chain_id}"
                )
                return True
            sleep(self._FUNDING_COOLDOWN_INTERVAL)
        print(
            f"[funder-check] cooldown expired for {chain_id} "
            "without reaching target balance",
            flush=True,
        )
        return False

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
