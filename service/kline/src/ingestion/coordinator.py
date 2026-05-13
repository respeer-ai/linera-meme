from dataclasses import dataclass

from ingestion.block_parser import LayerOneBlockParser
from ingestion.cursors import ChainCursor
from integration.chain_client import ChainClient
from integration.block_not_available_error import BlockNotAvailableError


@dataclass(slots=True)
class IngestionCoordinator:
    chain_client: ChainClient
    block_parser: LayerOneBlockParser
    raw_repository: object

    async def fetch_block_payload(self, chain_id: str, height: int) -> dict:
        return await self.chain_client.fetch_block(chain_id, height)

    async def ingest_from_cursor(self, cursor: ChainCursor, mode: str = 'live') -> dict:
        next_height = 0 if cursor.last_finalized_height is None else cursor.last_finalized_height + 1
        self.raw_repository.mark_attempt(cursor.chain_id, next_height)
        try:
            payload = await self.fetch_block_payload(cursor.chain_id, next_height)
            block = self.block_parser.parse(cursor.chain_id, next_height, payload)
            return self.raw_repository.ingest_block(block, mode=mode)
        except BlockNotAvailableError:
            raise
        except Exception as error:
            self.raw_repository.record_failed_ingest_run(
                cursor.chain_id,
                next_height,
                mode,
                str(error),
            )
            self.raw_repository.mark_failure(cursor.chain_id, next_height, str(error))
            raise
