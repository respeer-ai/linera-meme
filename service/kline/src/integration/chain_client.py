from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class BlockRef:
    chain_id: str
    height: int


class ChainClient(Protocol):
    async def fetch_block(self, ref: BlockRef) -> dict:
        """Fetch one chain block by chain_id and height."""

