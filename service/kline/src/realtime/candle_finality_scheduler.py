import asyncio
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor

from candle_schema import INTERVAL_BUCKET_MS
from realtime.market_data_event import MarketDataEvent


class CandleFinalityScheduler:
    def __init__(
        self,
        *,
        queue,
        pool_catalog_repository,
        account_codec,
        pool_catalog_repository_factory=None,
        interval_seconds: float = 1.0,
        emit_timeout_seconds: float = 5.0,
        now_ms=None,
    ):
        self.queue = queue
        self.pool_catalog_repository = pool_catalog_repository
        self.pool_catalog_repository_factory = pool_catalog_repository_factory
        self.account_codec = account_codec
        self.interval_seconds = interval_seconds
        self.emit_timeout_seconds = emit_timeout_seconds
        self.now_ms = now_ms or self._default_now_ms
        self._running = False
        self._emit_future = None
        self._executor = self._new_executor()
        self._last_finalized_bucket_by_pool_interval = {}
        self._thread_pool_catalog_repository = None
        self._retired_pool_catalog_repository_ids = set()
        self._pool_catalog_repository_lock = threading.Lock()

    async def run(self) -> None:
        self._running = True
        while self._running:
            try:
                await self._emit_due_events_async()
            except Exception as exc:
                print(f'Candle finality scheduler failed: {exc}')
                traceback.print_exc()
            await asyncio.sleep(self.interval_seconds)

    async def _emit_due_events_async(self) -> None:
        self._clear_finished_emit_future()
        if self._emit_future is not None and not self._emit_future.done():
            print('Candle finality scheduler skipped: emit still in flight')
            return
        loop = asyncio.get_running_loop()
        self._emit_future = loop.run_in_executor(self._executor, self.emit_due_events)
        try:
            await asyncio.wait_for(
                asyncio.shield(self._emit_future),
                timeout=self.emit_timeout_seconds,
            )
        except asyncio.TimeoutError:
            print(f'Candle finality scheduler timed out after {self.emit_timeout_seconds}s')
            self._reset_executor_after_timeout()
        finally:
            self._clear_finished_emit_future()

    def _clear_finished_emit_future(self) -> None:
        if self._emit_future is None or not self._emit_future.done():
            return
        try:
            self._emit_future.result()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            print(f'Candle finality scheduler failed: {exc}')
            traceback.print_exc()
        finally:
            self._emit_future = None

    def emit_due_events(self) -> None:
        now_ms = self.now_ms()
        pool_catalog_repository = self._pool_catalog_repository_for_worker()
        try:
            for pool in pool_catalog_repository.list_current_pool_views():
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
                        interval=interval,
                        event_time_ms=finalized_bucket_start,
                        updated_at_ms=now_ms,
                    ))
        finally:
            self._close_pool_catalog_repository_if_retired(pool_catalog_repository)

    def stop(self) -> None:
        self._running = False
        emit_running = self._emit_future is not None and not self._emit_future.done()
        if self._emit_future is not None:
            self._emit_future.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
        if emit_running:
            self._retire_thread_pool_catalog_repository()
        else:
            self._close_thread_pool_catalog_repository()

    def running(self) -> bool:
        return self._running

    def _default_now_ms(self) -> int:
        return int(__import__('time').time() * 1000)

    def _pool_catalog_repository_for_worker(self):
        if self.pool_catalog_repository_factory is None:
            return self.pool_catalog_repository
        with self._pool_catalog_repository_lock:
            if self._thread_pool_catalog_repository is None:
                self._thread_pool_catalog_repository = self.pool_catalog_repository_factory()
            return self._thread_pool_catalog_repository

    def _close_thread_pool_catalog_repository(self) -> None:
        repository = self._thread_pool_catalog_repository
        if repository is None:
            return
        close = getattr(repository, 'close', None)
        if close is not None:
            try:
                close()
            except Exception:
                pass
        self._thread_pool_catalog_repository = None

    def _reset_executor_after_timeout(self) -> None:
        if self._emit_future is not None:
            self._emit_future.cancel()
            self._emit_future = None
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._retire_thread_pool_catalog_repository()
        self._executor = self._new_executor()

    def _new_executor(self):
        return ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix='candle-finality',
        )

    def _retire_thread_pool_catalog_repository(self) -> None:
        with self._pool_catalog_repository_lock:
            repository = self._thread_pool_catalog_repository
            if repository is None:
                return
            self._retired_pool_catalog_repository_ids.add(id(repository))
            self._thread_pool_catalog_repository = None

    def _close_pool_catalog_repository_if_retired(self, repository) -> None:
        with self._pool_catalog_repository_lock:
            if id(repository) not in self._retired_pool_catalog_repository_ids:
                return
            self._retired_pool_catalog_repository_ids.remove(id(repository))
        close = getattr(repository, 'close', None)
        if close is not None:
            try:
                close()
            except Exception:
                pass
