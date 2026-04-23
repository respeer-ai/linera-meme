from ingestion.cursors import ChainCursor


class ChainCursorStore:
    """Loads persisted chain cursor state into ingestion-domain cursor objects."""

    def __init__(self, raw_repository):
        self.raw_repository = raw_repository

    def load(self, chain_id: str) -> ChainCursor:
        row = self.raw_repository.load_chain_cursor(chain_id)
        if row is None:
            return ChainCursor(chain_id=chain_id)
        return ChainCursor(
            chain_id=chain_id,
            last_finalized_height=row.get('last_finalized_height'),
            last_finalized_block_hash=row.get('last_finalized_block_hash'),
        )
