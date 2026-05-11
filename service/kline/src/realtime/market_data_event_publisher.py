import asyncio
import threading
import traceback
from concurrent.futures import ThreadPoolExecutor

from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError


class MarketDataEventPublisher:
    def __init__(
        self,
        *,
        queue,
        websocket_manager,
        payload_builder,
        drain_delay_seconds: float = 0.05,
        payload_builder_factory=None,
        build_timeout_seconds: float = 10.0,
    ):
        self.queue = queue
        self.websocket_manager = websocket_manager
        self.payload_builder = payload_builder
        self.drain_delay_seconds = drain_delay_seconds
        self.payload_builder_factory = payload_builder_factory
        self.build_timeout_seconds = build_timeout_seconds
        self._running = False
        self._thread_payload_builder = None
        self._retired_payload_builder_ids = set()
        self._payload_builder_lock = threading.Lock()
        self._build_future = None
        self._executor = self._new_executor()

    async def run(self) -> None:
        self._running = True
        while self._running:
            event = await self.queue.get()
            events = [event]
            if self.drain_delay_seconds > 0:
                await asyncio.sleep(self.drain_delay_seconds)
            events.extend(self.queue.drain_nowait())
            try:
                await self.publish(events)
            except ProjectionQueryUnavailableError as exc:
                print(f'Market data event publish skipped: {exc}')
            except Exception as exc:
                print(f'Market data event publish failed: {exc}')
                traceback.print_exc()

    async def publish(self, events: list) -> None:
        if not events:
            return
        payload = await self._build_payload_async(events)
        if payload.get('kline'):
            await self.websocket_manager.notify('kline', payload['kline'])
        if payload.get('transactions'):
            await self.websocket_manager.notify('transactions', payload['transactions'])
        if payload.get('positions', {}).get('events'):
            await self.websocket_manager.notify('positions', payload['positions'])

    def stop(self) -> None:
        self._running = False
        build_running = self._build_future is not None and not self._build_future.done()
        if self._build_future is not None:
            self._build_future.cancel()
        self._executor.shutdown(wait=False, cancel_futures=True)
        if build_running:
            self._retire_thread_payload_builder()
        else:
            self._close_thread_payload_builder()

    def running(self) -> bool:
        return self._running

    async def _build_payload_async(self, events: list) -> dict:
        self._clear_finished_build_future()
        if self._build_future is not None and not self._build_future.done():
            print('Market data event publish skipped: build still in flight')
            return {}
        loop = asyncio.get_running_loop()
        self._build_future = loop.run_in_executor(
            self._executor,
            self._build_payload,
            list(events),
        )
        try:
            return await asyncio.wait_for(
                asyncio.shield(self._build_future),
                timeout=self.build_timeout_seconds,
            )
        except asyncio.TimeoutError:
            print(f'Market data event publish timed out after {self.build_timeout_seconds}s')
            self._reset_executor_after_timeout()
            return {}
        finally:
            self._clear_finished_build_future()

    def _build_payload(self, events: list) -> dict:
        payload_builder = self._payload_builder_for_worker()
        try:
            return payload_builder.build(events)
        finally:
            self._close_payload_builder_if_retired(payload_builder)

    def _payload_builder_for_worker(self):
        if self.payload_builder_factory is None:
            return self.payload_builder
        with self._payload_builder_lock:
            if self._thread_payload_builder is None:
                self._thread_payload_builder = self.payload_builder_factory()
            return self._thread_payload_builder

    def _clear_finished_build_future(self) -> None:
        if self._build_future is None or not self._build_future.done():
            return
        try:
            self._build_future.result()
        except asyncio.CancelledError:
            pass
        except ProjectionQueryUnavailableError:
            raise
        except Exception as exc:
            print(f'Market data event publish failed: {exc}')
            traceback.print_exc()
        finally:
            self._build_future = None

    def _close_thread_payload_builder(self) -> None:
        builder = self._thread_payload_builder
        if builder is None:
            return
        close = getattr(builder, 'close', None)
        if close is not None:
            try:
                close()
            except Exception:
                pass
        self._thread_payload_builder = None

    def _reset_executor_after_timeout(self) -> None:
        if self._build_future is not None:
            self._build_future.cancel()
            self._build_future = None
        self._executor.shutdown(wait=False, cancel_futures=True)
        self._retire_thread_payload_builder()
        self._executor = self._new_executor()

    def _new_executor(self):
        return ThreadPoolExecutor(
            max_workers=1,
            thread_name_prefix='market-data-publisher',
        )

    def _retire_thread_payload_builder(self) -> None:
        with self._payload_builder_lock:
            builder = self._thread_payload_builder
            if builder is None:
                return
            self._retired_payload_builder_ids.add(id(builder))
            self._thread_payload_builder = None

    def _close_payload_builder_if_retired(self, builder) -> None:
        with self._payload_builder_lock:
            if id(builder) not in self._retired_payload_builder_ids:
                return
            self._retired_payload_builder_ids.remove(id(builder))
        close = getattr(builder, 'close', None)
        if close is not None:
            try:
                close()
            except Exception:
                pass
