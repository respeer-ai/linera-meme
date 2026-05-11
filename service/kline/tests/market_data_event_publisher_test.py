import sys
import asyncio
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from realtime.market_data_event import MarketDataEvent  # noqa: E402
from realtime.market_data_event_publisher import MarketDataEventPublisher  # noqa: E402
from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError  # noqa: E402


class FakeQueue:
    def drain_nowait(self):
        return []


class OneEventQueue:
    def __init__(self, event):
        self.event = event
        self.calls = 0

    async def get(self):
        self.calls += 1
        if self.calls == 1:
            return self.event
        await asyncio.Event().wait()

    def drain_nowait(self):
        return []


class FakePayloadBuilder:
    def __init__(self, payload):
        self.payload = payload
        self.events = None
        self.closed = False

    def build(self, events):
        self.events = events
        return self.payload

    def close(self):
        self.closed = True


class UnavailablePayloadBuilder:
    def build(self, events):
        raise ProjectionQueryUnavailableError('candles')


class MarketDataEventPublisherTest(unittest.IsolatedAsyncioTestCase):
    async def test_publish_fans_out_non_empty_topics_only(self):
        manager = AsyncMock()
        builder = FakePayloadBuilder({
            'kline': {'1min': [{'points': []}]},
            'transactions': [{'transactions': []}],
            'positions': {'events': [{'owner': 'owner'}]},
        })
        publisher = MarketDataEventPublisher(
            queue=FakeQueue(),
            websocket_manager=manager,
            payload_builder=builder,
        )
        events = [MarketDataEvent(event_type=MarketDataEvent.TYPE_SETTLED_TRADE)]

        await publisher.publish(events)

        self.assertEqual(builder.events, events)
        self.assertEqual(manager.notify.await_args_list[0].args, ('kline', {'1min': [{'points': []}]}))
        self.assertEqual(manager.notify.await_args_list[1].args, ('transactions', [{'transactions': []}]))
        self.assertEqual(manager.notify.await_args_list[2].args, ('positions', {'events': [{'owner': 'owner'}]}))

    async def test_run_skips_projection_unavailable_without_stopping(self):
        event = MarketDataEvent(event_type=MarketDataEvent.TYPE_SETTLED_TRADE)
        queue = OneEventQueue(event)
        manager = AsyncMock()
        publisher = MarketDataEventPublisher(
            queue=queue,
            websocket_manager=manager,
            payload_builder=UnavailablePayloadBuilder(),
            drain_delay_seconds=0,
        )

        task = asyncio.create_task(publisher.run())
        await asyncio.sleep(0.02)

        self.assertFalse(task.done())
        manager.notify.assert_not_awaited()
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

    async def test_publish_builds_payload_outside_event_loop_thread(self):
        loop_thread = threading.get_ident()
        build_thread = None

        class ThreadCapturingBuilder:
            def build(self, events):
                nonlocal build_thread
                build_thread = threading.get_ident()
                return {}

        publisher = MarketDataEventPublisher(
            queue=FakeQueue(),
            websocket_manager=AsyncMock(),
            payload_builder=ThreadCapturingBuilder(),
        )

        await publisher.publish([MarketDataEvent(event_type=MarketDataEvent.TYPE_SETTLED_TRADE)])
        publisher.stop()

        self.assertIsNotNone(build_thread)
        self.assertNotEqual(loop_thread, build_thread)

    async def test_timeout_recovers_next_build_without_waiting_for_stuck_thread(self):
        gate = threading.Event()
        calls = 0
        closed = 0

        class BlockingBuilder:
            def build(self, events):
                nonlocal calls
                calls += 1
                gate.wait(timeout=1)
                return {}

            def close(self):
                nonlocal closed
                closed += 1

        publisher = MarketDataEventPublisher(
            queue=FakeQueue(),
            websocket_manager=AsyncMock(),
            payload_builder=FakePayloadBuilder({}),
            payload_builder_factory=lambda: BlockingBuilder(),
            build_timeout_seconds=0.01,
        )

        started_at = time.time()
        await publisher.publish([MarketDataEvent(event_type=MarketDataEvent.TYPE_SETTLED_TRADE)])
        elapsed = time.time() - started_at
        await publisher.publish([MarketDataEvent(event_type=MarketDataEvent.TYPE_SETTLED_TRADE)])
        self.assertEqual(calls, 2)

        gate.set()
        for _ in range(20):
            if closed >= 1:
                break
            await asyncio.sleep(0.01)
        publisher.stop()

        self.assertLess(elapsed, 0.2)
        self.assertEqual(calls, 2)
        self.assertGreaterEqual(closed, 1)

    async def test_uses_thread_local_payload_builder_factory(self):
        main_builder = FakePayloadBuilder({})
        worker_builder = FakePayloadBuilder({})
        publisher = MarketDataEventPublisher(
            queue=FakeQueue(),
            websocket_manager=AsyncMock(),
            payload_builder=main_builder,
            payload_builder_factory=lambda: worker_builder,
        )
        event = MarketDataEvent(event_type=MarketDataEvent.TYPE_SETTLED_TRADE)

        await publisher.publish([event])
        publisher.stop()

        self.assertIsNone(main_builder.events)
        self.assertEqual(worker_builder.events, [event])
        self.assertTrue(worker_builder.closed)


if __name__ == '__main__':
    unittest.main()
