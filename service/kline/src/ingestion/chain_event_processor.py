import asyncio
import time


class ChainEventProcessor:
    """Processes chain update notifications by triggering bounded catch-up for that chain."""

    def __init__(
        self,
        catch_up_runner,
        max_blocks_per_chain: int,
        allowed_chain_ids: tuple[str, ...] = (),
        registry_refresh=None,
        business_freshness_service=None,
        task_timeout_seconds: float = 30.0,
        retry_delay_seconds: float = 0.05,
        retry_enabled: bool = True,
    ):
        self.catch_up_runner = catch_up_runner
        self.max_blocks_per_chain = int(max_blocks_per_chain)
        self.allowed_chain_ids = tuple(allowed_chain_ids)
        self.registry_refresh = registry_refresh
        self.business_freshness_service = business_freshness_service
        self.task_timeout_seconds = float(task_timeout_seconds)
        self.retry_delay_seconds = float(retry_delay_seconds)
        self.retry_enabled = bool(retry_enabled)
        self._chain_locks: dict[str, asyncio.Lock] = {}
        self._chain_tasks: dict[str, asyncio.Task] = {}
        self._pending_counts: dict[str, int] = {}
        self._last_results: dict[str, dict] = {}

    def add_chain_ids(self, chain_ids: list[str] | tuple[str, ...]) -> tuple[str, ...]:
        if not chain_ids:
            return self.allowed_chain_ids
        merged = set(self.allowed_chain_ids)
        merged.update(str(chain_id) for chain_id in chain_ids if str(chain_id).strip())
        self.allowed_chain_ids = tuple(sorted(merged))
        return self.allowed_chain_ids

    async def on_chain_notification(self, chain_id: str) -> dict:
        return await self._trigger(chain_id, trigger='notification')

    async def on_subscription_reconnect(self, chain_id: str) -> dict:
        return await self._trigger(chain_id, trigger='reconnect_reconcile')

    async def _trigger(self, chain_id: str, *, trigger: str) -> dict:
        refresh_result = await self._refresh_registry()
        if self.allowed_chain_ids and chain_id not in self.allowed_chain_ids:
            return {
                'trigger': trigger,
                'chain_id': chain_id,
                'accepted': False,
                'reason': 'chain_not_configured',
                'registry_refresh': refresh_result,
            }
        queued = self._enqueue_chain(chain_id)
        return {
            'trigger': trigger,
            'chain_id': chain_id,
            'accepted': True,
            'queued': queued,
            'registry_refresh': refresh_result,
            'last_result': self._last_results.get(chain_id),
        }

    async def _run_bounded_catch_up(self, chain_id: str) -> dict:
        started_at = int(time.time() * 1000)
        try:
            batch = await asyncio.wait_for(
                self.catch_up_runner.ingest_until_caught_up(
                    chain_id,
                    max_blocks=self.max_blocks_per_chain,
                    mode='catch_up',
                    drain_post_ingest=False,
                ),
                timeout=self.task_timeout_seconds,
            )
        except asyncio.TimeoutError:
            return {
                'chain_id': chain_id,
                'mode': 'catch_up',
                'batch_count': 0,
                'max_blocks_per_chain': self.max_blocks_per_chain,
                'ingested_count': 0,
                'caught_up': False,
                'timed_out': True,
                'error': f'catch-up task exceeded {self.task_timeout_seconds}s',
                'started_at_ms': started_at,
                'finished_at_ms': int(time.time() * 1000),
                'batches': [],
            }
        return {
            'chain_id': chain_id,
            'mode': 'catch_up',
            'batch_count': 1,
            'max_blocks_per_chain': self.max_blocks_per_chain,
            'ingested_count': int(batch.get('ingested_count', 0)),
            'caught_up': self._batch_caught_up(batch),
            'started_at_ms': started_at,
            'finished_at_ms': int(time.time() * 1000),
            'batches': [batch],
        }

    def _chain_lock(self, chain_id: str) -> asyncio.Lock:
        lock = self._chain_locks.get(chain_id)
        if lock is None:
            lock = asyncio.Lock()
            self._chain_locks[chain_id] = lock
        return lock

    def _enqueue_chain(self, chain_id: str) -> bool:
        self._pending_counts[chain_id] = self._pending_counts.get(chain_id, 0) + 1
        existing = self._chain_tasks.get(chain_id)
        if existing is not None and not existing.done():
            return False
        self._chain_tasks[chain_id] = asyncio.create_task(
            self._process_chain_until_idle(chain_id),
            name=f'chain-catch-up-worker-{chain_id}',
        )
        return True

    async def _process_chain_until_idle(self, chain_id: str) -> None:
        try:
            while self._pending_counts.get(chain_id, 0) > 0:
                self._pending_counts[chain_id] = 0
                async with self._chain_lock(chain_id):
                    try:
                        result = await self._run_bounded_catch_up(chain_id)
                    except Exception as error:
                        result = self._failed_result(chain_id, error)
                self._last_results[chain_id] = result
                await self._check_business_freshness(chain_id)
                if self.retry_enabled and self._needs_retry(result):
                    await asyncio.sleep(self.retry_delay_seconds)
                    self._pending_counts[chain_id] = self._pending_counts.get(chain_id, 0) + 1
        finally:
            task = self._chain_tasks.get(chain_id)
            if task is asyncio.current_task():
                self._chain_tasks.pop(chain_id, None)
            if self._pending_counts.get(chain_id, 0) > 0:
                self._enqueue_chain(chain_id)

    def _batch_caught_up(self, batch: dict) -> bool:
        if not batch.get('caught_up', False):
            return False
        post_ingest_result = batch.get('post_ingest_result')
        if isinstance(post_ingest_result, dict):
            return bool(post_ingest_result.get('caught_up', True))
        return True

    def _needs_retry(self, result: dict) -> bool:
        if result.get('timed_out'):
            return False
        return not bool(result.get('caught_up', False))

    def _failed_result(self, chain_id: str, error: Exception) -> dict:
        now_ms = int(time.time() * 1000)
        return {
            'chain_id': chain_id,
            'mode': 'catch_up',
            'batch_count': 0,
            'max_blocks_per_chain': self.max_blocks_per_chain,
            'ingested_count': 0,
            'caught_up': False,
            'error': str(error),
            'error_type': error.__class__.__name__,
            'started_at_ms': now_ms,
            'finished_at_ms': now_ms,
            'batches': [],
        }

    async def _check_business_freshness(self, chain_id: str) -> None:
        if self.business_freshness_service is None:
            return
        try:
            result = self.business_freshness_service.check(
                chain_id=chain_id,
                trigger='chain_catch_up',
            )
            if hasattr(result, '__await__'):
                await result
        except Exception as error:
            print(f'Failed check business freshness after chain catch-up: {error}')

    async def wait_for_idle(self, chain_id: str, timeout: float = 1.0) -> dict | None:
        task = self._chain_tasks.get(chain_id)
        if task is not None:
            await asyncio.wait_for(asyncio.shield(task), timeout=timeout)
        return self._last_results.get(chain_id)

    async def _refresh_registry(self):
        if self.registry_refresh is None:
            return None
        result = self.registry_refresh()
        if hasattr(result, '__await__'):
            return await result
        return result
