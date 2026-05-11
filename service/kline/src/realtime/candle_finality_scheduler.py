import asyncio
import traceback

from candle_schema import INTERVAL_BUCKET_MS
from realtime.market_data_event import MarketDataEvent


class CandleFinalityScheduler:
    def __init__(
        self,
        *,
        queue,
        pool_catalog_repository,
        account_codec,
        interval_seconds: float = 1.0,
        now_ms=None,
    ):
        self.queue = queue
        self.pool_catalog_repository = pool_catalog_repository
        self.account_codec = account_codec
        self.interval_seconds = interval_seconds
        self.now_ms = now_ms or self._default_now_ms
        self._running = False
        self._last_finalized_bucket_by_pool_interval = {}

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                self.emit_due_events()
            except Exception as exc:
                print(f'Candle finality scheduler failed: {exc}')
                traceback.print_exc()
            await asyncio.sleep(self.interval_seconds)

    def emit_due_events(self) -> None:
        now_ms = self.now_ms()
        for pool in self.pool_catalog_repository.list_current_pool_views():
            pool_application = self.account_codec.format_account(
                chain_id=pool.pool_application.chain_id,
                owner=pool.pool_application.owner,
            )
            for interval, bucket_ms in INTERVAL_BUCKET_MS.items():
                finalized_bucket_start = now_ms // bucket_ms * bucket_ms - bucket_ms
                key = (pool.pool_id, pool_application, interval)
                if finalized_bucket_start <= self._last_finalized_bucket_by_pool_interval.get(key, -1):
                    continue
                self._last_finalized_bucket_by_pool_interval[key] = finalized_bucket_start
                self.queue.put_nowait(MarketDataEvent(
                    event_type=MarketDataEvent.TYPE_CANDLE_FINALIZED,
                    pool_application=pool_application,
                    pool_id=pool.pool_id,
                    event_time_ms=finalized_bucket_start,
                    updated_at_ms=now_ms,
                ))

    def stop(self) -> None:
        self._running = False

    def running(self) -> bool:
        return self._running

    def _default_now_ms(self) -> int:
        return int(__import__('time').time() * 1000)

