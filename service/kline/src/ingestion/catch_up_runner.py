from integration.block_not_available_error import BlockNotAvailableError


class CatchUpRunner:
    """Advances persisted chain cursors until the node has no further finalized block."""

    def __init__(self, chain_cursor_store, ingestion_coordinator, post_ingest_pipeline=None):
        self.chain_cursor_store = chain_cursor_store
        self.ingestion_coordinator = ingestion_coordinator
        self.post_ingest_pipeline = post_ingest_pipeline

    async def ingest_next(self, chain_id: str, mode: str = 'catch_up') -> dict:
        cursor = self.chain_cursor_store.load(chain_id)
        return await self.ingestion_coordinator.ingest_from_cursor(cursor, mode=mode)

    async def ingest_until_caught_up(
        self,
        chain_id: str,
        *,
        max_blocks: int,
        mode: str = 'catch_up',
    ) -> dict:
        ingested = []
        for _ in range(int(max_blocks)):
            try:
                result = await self.ingest_next(chain_id, mode=mode)
            except BlockNotAvailableError:
                break
            ingested.append(result)
        post_ingest_result = None
        if ingested and self.post_ingest_pipeline is not None:
            post_ingest_result = self.post_ingest_pipeline.run_until_caught_up(
                reprocess_reason=f'{mode}:{chain_id}',
            )
        return {
            'chain_id': chain_id,
            'mode': mode,
            'ingested_count': len(ingested),
            'ingested': ingested,
            'caught_up': len(ingested) < int(max_blocks),
            'post_ingest_result': post_ingest_result,
        }
