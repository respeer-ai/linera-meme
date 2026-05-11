import asyncio
import traceback


class MarketDataEventPublisher:
    def __init__(
        self,
        *,
        queue,
        websocket_manager,
        payload_builder,
        drain_delay_seconds: float = 0.05,
    ):
        self.queue = queue
        self.websocket_manager = websocket_manager
        self.payload_builder = payload_builder
        self.drain_delay_seconds = drain_delay_seconds
        self._running = False

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
            except Exception as exc:
                print(f'Market data event publish failed: {exc}')
                traceback.print_exc()

    async def publish(self, events: list) -> None:
        if not events:
            return
        payload = await asyncio.to_thread(self.payload_builder.build, events)
        if payload.get('kline'):
            await self.websocket_manager.notify('kline', payload['kline'])
        if payload.get('transactions'):
            await self.websocket_manager.notify('transactions', payload['transactions'])
        if payload.get('positions', {}).get('events'):
            await self.websocket_manager.notify('positions', payload['positions'])

    def stop(self) -> None:
        self._running = False

    def running(self) -> bool:
        return self._running

