"""Command to fund chains from a source wallet or faucet claim."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import monotonic, sleep

from linest.client.funder_pool import FunderPool
from linest.client.linera_client import LineraClient
from linest.config import NetworkConfig, WalletPaths
from linest.domain_registry import DomainRegistry
from linest.errors import DeploymentError, LinestError
from linest.registry import DeploymentRegistry


class FundCommand:
    """Top up chain balances from a source wallet or on-demand faucet claims."""

    _TRANSFER_FEE_BUFFER: float = 0.001
    _FUNDING_COOLDOWN_SECONDS: float = 60.0
    _FUNDING_COOLDOWN_INTERVAL: float = 2.0

    def __init__(
        self,
        config: NetworkConfig,
        registry: DeploymentRegistry,
        linera_client: LineraClient,
        base_dir: Path,
        domain_registry: DomainRegistry | None = None,
    ) -> None:
        self.config = config
        self.registry = registry
        self.linera_client = linera_client
        self.base_dir = base_dir
        self.domain_registry = domain_registry

    def fund_chains(
        self,
        min_balance: float,
        source_wallet_dir: Path | None = None,
        faucet_url: str | None = None,
    ) -> None:
        """Fund all known chains to at least ``min_balance``.

        Exactly one of ``source_wallet_dir`` or ``faucet_url`` must be provided.
        When ``faucet_url`` is provided, funder chains are claimed on demand into
        separate wallet directories and consumed until all targets are funded.
        """
        if (source_wallet_dir is None) == (faucet_url is None):
            raise LinestError(
                "Provide either --source-wallet-dir or --claim-from-faucet "
                "with --faucet-url"
            )

        if source_wallet_dir is not None:
            source_paths = WalletPaths.from_wallet_dir(source_wallet_dir)
            self._validate_source_wallet(source_paths)
        else:
            assert faucet_url is not None
            self._ensure_funder_exists(faucet_url)

        target_chains = self._collect_target_chain_ids()
        if not target_chains:
            print("No target chains found in registry; nothing to fund.", flush=True)
            return

        if source_wallet_dir is not None:
            self._fund_from_wallet(source_paths, target_chains, min_balance)
        else:
            self._fund_from_faucet(faucet_url, target_chains, min_balance)

    def _validate_source_wallet(self, source_paths: WalletPaths) -> None:
        """Raise an error if the provided source wallet does not exist."""
        if not source_paths.wallet.exists():
            raise LinestError(
                f"Source wallet not found: {source_paths.wallet.parent}"
            )

    def _ensure_funder_exists(self, faucet_url: str) -> str:
        """Ensure at least one funder chain is available, claiming if necessary."""
        pool = FunderPool(
            base_dir=self.base_dir,
            env=self.config.env,
            faucet_url=faucet_url,
            linera_client=self.linera_client,
        )
        return pool.ensure_one()

    def list_funders(self) -> list[dict[str, str]]:
        """Return all claimed funder chains and their balances."""
        pool = FunderPool(
            base_dir=self.base_dir,
            env=self.config.env,
            faucet_url="",
            linera_client=self.linera_client,
        )
        return pool.list_funders()

    def clean_funders(self) -> int:
        """Remove spent funder wallets and return the number removed."""
        pool = FunderPool(
            base_dir=self.base_dir,
            env=self.config.env,
            faucet_url="",
            linera_client=self.linera_client,
        )
        return pool.clean_spent()

    def _collect_target_chain_ids(self) -> set[str]:
        """Return all chain IDs that should be funded from the registries."""
        chain_ids: set[str] = set()
        for family in self.registry.list_families():
            if family.creator_chain_id:
                chain_ids.add(family.creator_chain_id)
            for version_record in family.versions.values():
                chain_ids.update(
                    self._deployment_chain_ids(version_record.business_app)
                )
                for state_app_name in version_record.state_apps:
                    chain_ids.update(self._deployment_chain_ids(state_app_name))
        if self.domain_registry is not None:
            for entry in self.domain_registry.load().values():
                chain_id = entry.get("chain_id")
                if chain_id:
                    chain_ids.add(chain_id)
        return chain_ids

    def _deployment_chain_ids(self, deployment_name: str) -> set[str]:
        """Return the creator chain ID for a concrete deployment, if known."""
        try:
            deployment = self.registry.load_deployment(deployment_name)
            return {deployment.creator_chain_id}
        except (DeploymentError, FileNotFoundError):
            return set()

    def _fund_from_wallet(
        self,
        source_paths: WalletPaths,
        target_chains: set[str],
        min_balance: float,
    ) -> None:
        """Fund target chains from an existing source wallet."""
        source_chain_id = self.linera_client.default_chain_id_for(
            source_paths.wallet,
            source_paths.keystore,
            source_paths.storage,
        )
        for chain_id in sorted(target_chains):
            self._ensure_funded(
                source_paths,
                source_chain_id,
                chain_id,
                min_balance,
            )

    def _fund_from_faucet(
        self,
        faucet_url: str,
        target_chains: set[str],
        min_balance: float,
    ) -> None:
        """Fund target chains by claiming funder chains on demand."""
        pool = FunderPool(
            base_dir=self.base_dir,
            env=self.config.env,
            faucet_url=faucet_url,
            linera_client=self.linera_client,
        )
        for chain_id in sorted(target_chains):
            self._ensure_funded_from_pool(pool, chain_id, min_balance)

    def _ensure_funded_from_pool(
        self,
        pool: FunderPool,
        target_chain_id: str,
        min_balance: float,
    ) -> None:
        """Top up a single target chain using on-demand funder claims."""
        target_paths = self._target_wallet_paths(target_chain_id)
        while True:
            current_balance = self.linera_client.query_balance(
                target_paths.wallet,
                target_paths.keystore,
                target_paths.storage,
                target_chain_id,
            )
            if current_balance >= min_balance:
                print(
                    f"Chain {target_chain_id} balance {current_balance} "
                    f">= {min_balance}",
                    flush=True,
                )
                return

            funder_chain_id = pool.next_available_chain_id()
            funder_dir = pool.wallet_dir_for(funder_chain_id)
            funder_paths = WalletPaths.from_wallet_dir(funder_dir)
            funder_balance = self.linera_client.query_balance(
                funder_paths.wallet,
                funder_paths.keystore,
                funder_paths.storage,
                funder_chain_id,
            )
            transfer_amount = funder_balance - self._TRANSFER_FEE_BUFFER
            if transfer_amount <= 0:
                continue

            print(
                f"Funding chain {target_chain_id} from funder {funder_chain_id}: "
                f"transfer {transfer_amount}",
                flush=True,
            )
            self.linera_client.transfer(
                funder_paths.wallet,
                funder_paths.keystore,
                funder_paths.storage,
                funder_chain_id,
                target_chain_id,
                f"{transfer_amount:.10g}",
            )
            pool.mark_spent(funder_chain_id)
            print(
                f"Funding chain {target_chain_id}: transfer complete",
                flush=True,
            )
            if self._wait_for_balance(
                target_paths, target_chain_id, min_balance
            ):
                return

    def _ensure_funded(
        self,
        source_paths: WalletPaths,
        source_chain_id: str,
        target_chain_id: str,
        min_balance: float,
    ) -> None:
        """Top up a single target chain from a reusable source wallet."""
        if target_chain_id == source_chain_id:
            return

        target_paths = self._target_wallet_paths(target_chain_id)
        current_balance = self.linera_client.query_balance(
            target_paths.wallet,
            target_paths.keystore,
            target_paths.storage,
            target_chain_id,
        )

        if current_balance >= min_balance:
            print(
                f"Chain {target_chain_id} balance {current_balance} >= {min_balance}",
                flush=True,
            )
            return

        amount = min_balance - current_balance + self._TRANSFER_FEE_BUFFER
        print(
            f"Funding chain {target_chain_id}: "
            f"{current_balance} -> {min_balance} (transfer {amount})",
            flush=True,
        )
        self.linera_client.transfer(
            source_paths.wallet,
            source_paths.keystore,
            source_paths.storage,
            source_chain_id,
            target_chain_id,
            f"{amount:.10g}",
        )
        self._wait_for_balance(target_paths, target_chain_id, min_balance)

    def _wait_for_balance(
        self,
        paths: WalletPaths,
        chain_id: str,
        min_balance: float,
    ) -> bool:
        """Wait for a funding transfer to land by polling inbox and balance.

        Returns ``True`` as soon as the balance reaches ``min_balance``.
        Returns ``False`` if the cooldown expires without the balance arriving.
        """
        deadline = monotonic() + self._FUNDING_COOLDOWN_SECONDS
        while monotonic() < deadline:
            self.linera_client.process_inbox(
                paths.wallet, paths.keystore, paths.storage
            )
            balance = self.linera_client.query_balance(
                paths.wallet,
                paths.keystore,
                paths.storage,
                chain_id,
            )
            if balance >= min_balance:
                print(
                    f"Chain {chain_id} balance {balance} >= {min_balance} "
                    "after funding",
                    flush=True,
                )
                return True
            sleep(self._FUNDING_COOLDOWN_INTERVAL)
        return False

    def _target_wallet_paths(self, chain_id: str) -> "WalletPaths":
        """Return wallet paths capable of querying the target chain.

        Chains were created from app-specific creator wallets, so we probe the
        wallets for every known app family and every domain-registered app.
        """
        candidate_dirs = self._candidate_wallet_dirs()
        for wallet_dir in candidate_dirs:
            paths = WalletPaths.from_wallet_dir(wallet_dir)
            try:
                self.linera_client.query_balance(
                    paths.wallet,
                    paths.keystore,
                    paths.storage,
                    chain_id,
                )
                return paths
            except Exception:
                continue
        raise DeploymentError(f"No wallet found for target chain {chain_id}")

    def _candidate_wallet_dirs(self) -> list[Path]:
        """Return all wallet directories that may own a target chain."""
        base = Path(self.config.wallet_dir)
        names: set[str] = set()
        for family in self.registry.list_families():
            names.add(family.name)
        if self.domain_registry is not None:
            names.update(self.domain_registry.load().keys())
        return [base / name / "0" for name in sorted(names)]
