import asyncio

from realtime.market_data_event import MarketDataEvent


class MarketDataEventQueue:
    def __init__(self, *, maxsize: int = 0):
        self._queue = asyncio.Queue(maxsize=maxsize)

    async def put(self, event: MarketDataEvent) -> None:
        await self._queue.put(event)

    def put_nowait(self, event: MarketDataEvent) -> None:
        self._queue.put_nowait(event)

    async def get(self) -> MarketDataEvent:
        return await self._queue.get()

    def drain_nowait(self) -> list[MarketDataEvent]:
        events = []
        while True:
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                return events

