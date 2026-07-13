"""Layout of wallet directories for an application family."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from linest.config import WalletPaths


@dataclass(frozen=True)
class AppWalletLayout:
    """Paths to the wallets belonging to a single application family.

    The layout follows the convention ``<wallet_dir>/<app_name>/<index>/``,
    where ``index`` is ``creator`` for the publisher/creator wallet or a
    zero-based integer for owner wallets.
    """

    wallet_dir: Path
    app_name: str

    def creator(self) -> WalletPaths:
        """Return the paths for the creator/publisher wallet."""
        return self._index("creator")

    def owner(self, index: int) -> WalletPaths:
        """Return the paths for the owner wallet at the given index."""
        return self._index(str(index))

    def _index(self, index: str) -> WalletPaths:
        """Return wallet paths for the given sub-directory index."""
        return WalletPaths.from_wallet_dir(
            self.wallet_dir / self.app_name / index
        )
