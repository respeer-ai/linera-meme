from typing import Protocol


class ChainClient(Protocol):
    async def fetch_block(self, chain_id: str, height: int) -> dict:
        """Fetch one chain block by chain_id and height."""
