import asyncio


class ChainEventProcessor:
    """Processes chain update notifications by triggering bounded catch-up for that chain."""

    def __init__(
        self,
        catch_up_runner,
        max_blocks_per_chain: int,
        allowed_chain_ids: tuple[str, ...] = (),
    ):
        self.catch_up_runner = catch_up_runner
        self.max_blocks_per_chain = int(max_blocks_per_chain)
        self.allowed_chain_ids = tuple(allowed_chain_ids)
        self._chain_locks: dict[str, asyncio.Lock] = {}

    async def on_chain_notification(self, chain_id: str) -> dict:
        return await self._trigger(chain_id, trigger='notification')

    async def on_subscription_reconnect(self, chain_id: str) -> dict:
        return await self._trigger(chain_id, trigger='reconnect_reconcile')

    async def _trigger(self, chain_id: str, *, trigger: str) -> dict:
        if self.allowed_chain_ids and chain_id not in self.allowed_chain_ids:
            return {
                'trigger': trigger,
                'chain_id': chain_id,
                'accepted': False,
                'reason': 'chain_not_configured',
            }
        async with self._chain_lock(chain_id):
            result = await self._ingest_until_idle(chain_id)
        return {
            'trigger': trigger,
            'chain_id': chain_id,
            'accepted': True,
            'result': result,
        }

    async def _ingest_until_idle(self, chain_id: str) -> dict:
        batches = []
        total_ingested_count = 0
        while True:
            batch = await self.catch_up_runner.ingest_until_caught_up(
                chain_id,
                max_blocks=self.max_blocks_per_chain,
                mode='catch_up',
            )
            batches.append(batch)
            total_ingested_count += int(batch.get('ingested_count', 0))
            if batch.get('caught_up', False):
                return {
                    'chain_id': chain_id,
                    'mode': 'catch_up',
                    'batch_count': len(batches),
                    'max_blocks_per_chain': self.max_blocks_per_chain,
                    'ingested_count': total_ingested_count,
                    'caught_up': True,
                    'batches': batches,
                }

    def _chain_lock(self, chain_id: str) -> asyncio.Lock:
        lock = self._chain_locks.get(chain_id)
        if lock is None:
            lock = asyncio.Lock()
            self._chain_locks[chain_id] = lock
        return lock
