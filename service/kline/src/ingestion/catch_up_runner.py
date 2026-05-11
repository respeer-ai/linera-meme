import asyncio
from concurrent.futures import Future, ThreadPoolExecutor

from integration.block_not_available_error import BlockNotAvailableError


class CatchUpRunner:
    """Advances persisted chain cursors until the node has no further finalized block."""

    def __init__(
        self,
        chain_cursor_store,
        ingestion_coordinator,
        post_ingest_pipeline=None,
        post_ingest_pipeline_factory=None,
        post_ingest_timeout_seconds: float = 25.0,
    ):
        self.chain_cursor_store = chain_cursor_store
        self.ingestion_coordinator = ingestion_coordinator
        self.post_ingest_pipeline = post_ingest_pipeline
        self.post_ingest_pipeline_factory = post_ingest_pipeline_factory
        self.post_ingest_timeout_seconds = float(post_ingest_timeout_seconds)
        self._post_ingest_executor = self._new_post_ingest_executor()
        self._post_ingest_future: Future | None = None

    async def ingest_next(self, chain_id: str, mode: str = 'catch_up') -> dict:
        cursor = self.chain_cursor_store.load(chain_id)
        return await self.ingestion_coordinator.ingest_from_cursor(cursor, mode=mode)

    async def ingest_until_caught_up(
        self,
        chain_id: str,
        *,
        max_blocks: int,
        mode: str = 'catch_up',
        drain_post_ingest: bool = False,
    ) -> dict:
        ingested = []
        for _ in range(int(max_blocks)):
            try:
                result = await self.ingest_next(chain_id, mode=mode)
            except BlockNotAvailableError:
                break
            ingested.append(result)
        post_ingest_result = None
        if ingested and self._has_post_ingest_pipeline():
            post_ingest_result = await self._run_post_ingest(
                chain_id=chain_id,
                mode=mode,
                drain_post_ingest=drain_post_ingest,
            )
        return {
            'chain_id': chain_id,
            'mode': mode,
            'ingested_count': len(ingested),
            'ingested': ingested,
            'caught_up': len(ingested) < int(max_blocks),
            'post_ingest_result': post_ingest_result,
        }

    async def _run_post_ingest(
        self,
        *,
        chain_id: str,
        mode: str,
        drain_post_ingest: bool,
    ) -> dict:
        if self._post_ingest_future is not None and not self._post_ingest_future.done():
            return {
                'reprocess_reason': f'{mode}:{chain_id}',
                'caught_up': False,
                'skipped': True,
                'reason': 'post_ingest_in_flight',
            }
        method_name = 'run_until_caught_up' if drain_post_ingest else 'run_bounded'
        self._post_ingest_future = self._post_ingest_executor.submit(
            self._run_post_ingest_pipeline,
            method_name,
            f'{mode}:{chain_id}',
        )
        try:
            return await asyncio.wait_for(
                asyncio.shield(asyncio.wrap_future(self._post_ingest_future)),
                timeout=self.post_ingest_timeout_seconds,
            )
        except asyncio.TimeoutError:
            self._reset_post_ingest_executor()
            return {
                'reprocess_reason': f'{mode}:{chain_id}',
                'caught_up': False,
                'timed_out': True,
                'error': f'post-ingest exceeded {self.post_ingest_timeout_seconds}s',
            }
        except asyncio.CancelledError:
            self._reset_post_ingest_executor()
            raise
        finally:
            if self._post_ingest_future is not None and self._post_ingest_future.done():
                self._post_ingest_future = None

    def shutdown(self) -> None:
        self._post_ingest_executor.shutdown(wait=False, cancel_futures=True)

    def _run_post_ingest_pipeline(self, method_name: str, reprocess_reason: str) -> dict:
        pipeline = self.post_ingest_pipeline
        if self.post_ingest_pipeline_factory is not None:
            pipeline = self.post_ingest_pipeline_factory()
        close = getattr(pipeline, 'close', None)
        try:
            return getattr(pipeline, method_name)(reprocess_reason=reprocess_reason)
        finally:
            if self.post_ingest_pipeline_factory is not None and close is not None:
                close()

    def _has_post_ingest_pipeline(self) -> bool:
        return self.post_ingest_pipeline is not None or self.post_ingest_pipeline_factory is not None

    def _reset_post_ingest_executor(self) -> None:
        if self._post_ingest_future is not None:
            self._post_ingest_future.cancel()
            self._post_ingest_future = None
        self._post_ingest_executor.shutdown(wait=False, cancel_futures=True)
        self._post_ingest_executor = self._new_post_ingest_executor()

    def _new_post_ingest_executor(self):
        return ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix='kline-post-ingest',
        )
