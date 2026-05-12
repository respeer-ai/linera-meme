import asyncio
import threading
import time

from realtime.market_data_event import MarketDataEvent


class MarketDataEventQueue:
    def __init__(self, *, maxsize: int = 0, diagnostic_recorder=None):
        self._queue = asyncio.Queue(maxsize=maxsize)
        self.diagnostic_recorder = diagnostic_recorder
        self._loop = None
        self._loop_thread_id = None

    async def put(self, event: MarketDataEvent) -> None:
        self._bind_running_loop()
        await self._queue.put(event)

    def put_nowait(self, event: MarketDataEvent) -> None:
        if self._should_schedule_threadsafe():
            self._record_event(stage='enqueue_threadsafe_scheduled', event=event)
            self._loop.call_soon_threadsafe(self._queue.put_nowait, event)
            return
        self._record_event(stage='enqueue_inline', event=event)
        self._queue.put_nowait(event)

    async def get(self) -> MarketDataEvent:
        self._bind_running_loop()
        return await self._queue.get()

    def drain_nowait(self) -> list[MarketDataEvent]:
        self._bind_running_loop_if_available()
        events = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                return events

    def _bind_running_loop(self) -> None:
        loop = asyncio.get_running_loop()
        if self._loop is loop:
            return
        self._loop = loop
        self._loop_thread_id = threading.get_ident()

    def _bind_running_loop_if_available(self) -> None:
        try:
            self._bind_running_loop()
        except RuntimeError:
            return

    def _should_schedule_threadsafe(self) -> bool:
        return (
            self._loop is not None
            and self._loop.is_running()
            and self._loop_thread_id is not None
            and threading.get_ident() != self._loop_thread_id
        )

    def _record_event(self, *, stage: str, event: MarketDataEvent) -> None:
        if self.diagnostic_recorder is None:
            return
        self.diagnostic_recorder.record(
            stage=stage,
            event_type=event.event_type,
            pool_application=event.pool_application,
            pool_id=event.pool_id,
            transaction_id=event.transaction_id,
            event_time_ms=event.event_time_ms,
            queue_lag_ms=self._lag_ms(event),
            thread_id=threading.get_ident(),
        )

    def _lag_ms(self, event: MarketDataEvent) -> int | None:
        if event.updated_at_ms is None:
            return None
        return max(0, int(time.time() * 1000) - int(event.updated_at_ms))
