from dataclasses import dataclass

from ingestion.cursors import ChainCursor
from integration.chain_client import ChainClient


@dataclass(slots=True)
class IngestionCoordinator:
    chain_client: ChainClient
    raw_repository: object

    async def fetch_block(self, chain_id: str, height: int) -> dict:
        return await self.chain_client.fetch_block(chain_id, height)

    async def ingest_from_cursor(self, cursor: ChainCursor, mode: str = 'live') -> dict:
        next_height = 0 if cursor.last_finalized_height is None else cursor.last_finalized_height + 1
        self.raw_repository.mark_attempt(cursor.chain_id, next_height)
        try:
            block = await self.fetch_block(cursor.chain_id, next_height)
            return self.raw_repository.ingest_block(block, mode=mode)
        except Exception as error:
            self.raw_repository.mark_failure(cursor.chain_id, next_height, str(error))
            raise
