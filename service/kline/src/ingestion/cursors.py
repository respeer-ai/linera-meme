from dataclasses import dataclass


@dataclass(slots=True)
class ChainCursor:
    chain_id: str
    last_finalized_height: int | None = None
    last_finalized_block_hash: str | None = None

