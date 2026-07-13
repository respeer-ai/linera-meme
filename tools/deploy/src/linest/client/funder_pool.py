"""On-demand funder chain management for claim-mode funding."""

from __future__ import annotations

from pathlib import Path

from linest.client.linera_client import LineraClient
from linest.config import WalletPaths
from linest.errors import LinestError, LineraCliError


class FunderPool:
    """Claim funder chains from a faucet and consume them one by one."""

    _FUNDER_DIR_NAME: str = "funder"
    _SPENT_BALANCE_THRESHOLD: float = 0.01
    _GAS_RESERVE: float = 0.001

    def __init__(
        self,
        base_dir: Path,
        env: str,
        faucet_url: str,
        linera_client: LineraClient,
    ) -> None:
        self.base_dir = base_dir
        self.env = env
        self.faucet_url = faucet_url
        self.linera_client = linera_client
        self.chain_dir = base_dir / self._FUNDER_DIR_NAME / env / "chains"
        self.chain_dir.mkdir(parents=True, exist_ok=True)

    def ensure_one(self) -> str:
        """Return an existing or newly claimed funder chain ID."""
        print("[funder] looking for an available funder chain", flush=True)
        chain_id = self.next_available_chain_id(claim_if_empty=True)
        print(f"[funder] using funder chain {chain_id}", flush=True)
        return chain_id

    def next_available_chain_id(self, claim_if_empty: bool = True) -> str:
        """Return a funder chain with remaining balance.

        If no available chain exists and ``claim_if_empty`` is True, a new
        chain is claimed from the faucet.
        """
        for wallet_dir in sorted(self.chain_dir.iterdir()):
            if not wallet_dir.is_dir():
                continue
            if self._is_spent(wallet_dir):
                continue
            chain_id = self._try_use_chain(wallet_dir)
            if chain_id:
                return chain_id

        if claim_if_empty:
            return self._claim_new_chain()

        raise LinestError("No available funder chain")

    def _try_use_chain(self, wallet_dir: Path) -> str | None:
        """Return the chain ID if this funder wallet still has balance."""
        paths = WalletPaths.from_wallet_dir(wallet_dir)
        if not paths.wallet.exists():
            return None
        try:
            chain_id = self.linera_client.default_chain_id_for(
                paths.wallet, paths.keystore, paths.storage
            )
            print(f"[funder] checking balance of funder {chain_id}", flush=True)
            balance = self.linera_client.query_balance(
                paths.wallet, paths.keystore, paths.storage, chain_id
            )
            print(f"[funder] funder {chain_id} balance {balance}", flush=True)
            if balance > self._SPENT_BALANCE_THRESHOLD:
                return chain_id
            self._mark_spent(wallet_dir)
        except LineraCliError as exc:
            print(f"[funder] failed to use funder wallet {wallet_dir}: {exc}", flush=True)
            return None
        return None

    def _claim_new_chain(self) -> str:
        """Claim a new funder chain and return its chain ID."""
        wallet_dir = self._allocate_wallet_dir()
        print(f"[funder] claiming new funder wallet at {wallet_dir}", flush=True)
        wallet_dir.mkdir(parents=True, exist_ok=True)
        paths = WalletPaths.from_wallet_dir(wallet_dir)
        print("[funder] initializing funder wallet", flush=True)
        self.linera_client.init_wallet(
            paths.wallet, paths.keystore, paths.storage, self.faucet_url
        )
        print("[funder] requesting funder chain from faucet", flush=True)
        self.linera_client.request_chain(
            paths.wallet, paths.keystore, paths.storage, self.faucet_url
        )
        chain_id = self.linera_client.default_chain_id_for(
            paths.wallet, paths.keystore, paths.storage
        )
        print(f"[funder] claimed funder chain {chain_id}", flush=True)
        return chain_id

    def _allocate_wallet_dir(self) -> Path:
        """Return the next unused funder wallet directory."""
        index = 0
        while True:
            candidate = self.chain_dir / str(index)
            if not candidate.exists():
                return candidate
            index += 1

    def wallet_dir_for(self, chain_id: str) -> Path:
        """Return the wallet directory that owns the given funder chain ID."""
        for wallet_dir in sorted(self.chain_dir.iterdir()):
            if not wallet_dir.is_dir():
                continue
            paths = WalletPaths.from_wallet_dir(wallet_dir)
            if not paths.wallet.exists():
                continue
            try:
                candidate_id = self.linera_client.default_chain_id_for(
                    paths.wallet, paths.keystore, paths.storage
                )
                if candidate_id == chain_id:
                    return wallet_dir
            except LineraCliError:
                continue
        raise LinestError(f"Funder wallet not found for chain {chain_id}")

    def mark_spent(self, chain_id: str) -> None:
        """Mark a funder chain as spent so it is skipped in future scans."""
        try:
            wallet_dir = self.wallet_dir_for(chain_id)
            self._mark_spent(wallet_dir)
        except LinestError:
            pass

    def _mark_spent(self, wallet_dir: Path) -> None:
        """Create a spent marker file in the funder wallet directory."""
        (wallet_dir / ".spent").touch()

    def _is_spent(self, wallet_dir: Path) -> bool:
        """Return True if the funder wallet has a spent marker."""
        return (wallet_dir / ".spent").exists()

    def list_funders(self) -> list[dict[str, str]]:
        """Return a list of funder chain IDs and their wallet directories."""
        funders: list[dict[str, str]] = []
        for wallet_dir in sorted(self.chain_dir.iterdir()):
            if not wallet_dir.is_dir():
                continue
            paths = WalletPaths.from_wallet_dir(wallet_dir)
            if not paths.wallet.exists():
                continue
            try:
                chain_id = self.linera_client.default_chain_id_for(
                    paths.wallet, paths.keystore, paths.storage
                )
                balance = self.linera_client.query_balance(
                    paths.wallet, paths.keystore, paths.storage, chain_id
                )
                funders.append(
                    {
                        "chain_id": chain_id,
                        "wallet_dir": str(wallet_dir),
                        "balance": str(balance),
                    }
                )
            except LineraCliError:
                continue
        return funders

    def clean_spent(self) -> int:
        """Remove funder wallets whose balance is below the spent threshold."""
        removed = 0
        for wallet_dir in sorted(self.chain_dir.iterdir()):
            if not wallet_dir.is_dir():
                continue
            paths = WalletPaths.from_wallet_dir(wallet_dir)
            if not paths.wallet.exists():
                continue
            try:
                chain_id = self.linera_client.default_chain_id_for(
                    paths.wallet, paths.keystore, paths.storage
                )
                balance = self.linera_client.query_balance(
                    paths.wallet, paths.keystore, paths.storage, chain_id
                )
                if balance <= self._SPENT_BALANCE_THRESHOLD or self._is_spent(wallet_dir):
                    self._remove_wallet_dir(wallet_dir)
                    removed += 1
            except LineraCliError:
                continue
        return removed

    @staticmethod
    def _remove_wallet_dir(wallet_dir: Path) -> None:
        """Recursively remove a wallet directory."""
        import shutil

        shutil.rmtree(wallet_dir, ignore_errors=True)
