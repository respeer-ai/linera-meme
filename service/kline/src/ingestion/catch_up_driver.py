class CatchUpDriver:
    """Runs bounded catch-up batches for a configured set of chains."""

    def __init__(self, catch_up_runner, chain_ids: tuple[str, ...], max_blocks_per_chain: int):
        self.catch_up_runner = catch_up_runner
        self.chain_ids = tuple(chain_ids)
        self.max_blocks_per_chain = int(max_blocks_per_chain)

    async def run_once(self, *, max_blocks_per_chain: int | None = None) -> dict:
        results = []
        total_ingested = 0
        effective_max_blocks = (
            self.max_blocks_per_chain
            if max_blocks_per_chain is None
            else int(max_blocks_per_chain)
        )
        for chain_id in self.chain_ids:
            result = await self.catch_up_runner.ingest_until_caught_up(
                chain_id,
                max_blocks=effective_max_blocks,
            )
            results.append(result)
            total_ingested += int(result.get('ingested_count', 0))
        return {
            'chain_ids': list(self.chain_ids),
            'chain_count': len(self.chain_ids),
            'max_blocks_per_chain': effective_max_blocks,
            'total_ingested_count': total_ingested,
            'results': results,
        }
