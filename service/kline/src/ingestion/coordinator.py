from dataclasses import dataclass

from ingestion.cursors import ChainCursor
from integration.chain_client import BlockRef, ChainClient


@dataclass(slots=True)
class IngestionCoordinator:
    chain_client: ChainClient
    raw_repository: object

    async def fetch_block(self, chain_id: str, height: int) -> dict:
        return await self.chain_client.fetch_block(BlockRef(chain_id=chain_id, height=height))

    async def ingest_from_cursor(self, cursor: ChainCursor) -> dict:
        next_height = 0 if cursor.last_finalized_height is None else cursor.last_finalized_height + 1
        return await self.fetch_block(cursor.chain_id, next_height)

