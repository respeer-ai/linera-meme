import asyncio
import threading
import unittest
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from realtime.market_data_event import MarketDataEvent  # noqa: E402
from realtime.market_data_event_queue import MarketDataEventQueue  # noqa: E402


class FakeDiagnosticRecorder:
    def __init__(self):
        self.records = []

    def record(self, **kwargs):
        self.records.append(dict(kwargs))


class MarketDataEventQueueTest(unittest.IsolatedAsyncioTestCase):
    async def test_put_nowait_from_worker_thread_wakes_event_loop_getter(self):
        queue = MarketDataEventQueue()
        ready = threading.Event()
        event = MarketDataEvent(
            event_type=MarketDataEvent.TYPE_SETTLED_TRADE,
            pool_application='pool-app',
            transaction_id=10,
        )

        async def consumer():
            ready.set()
            return await queue.get()

        task = asyncio.create_task(consumer())
        await asyncio.to_thread(ready.wait, 1)

        def producer():
            queue.put_nowait(event)

        producer_thread = threading.Thread(target=producer)
        producer_thread.start()
        producer_thread.join(timeout=1)

        received = await asyncio.wait_for(task, timeout=0.2)

        self.assertEqual(received, event)

    async def test_put_nowait_from_worker_thread_records_threadsafe_enqueue(self):
        recorder = FakeDiagnosticRecorder()
        queue = MarketDataEventQueue(diagnostic_recorder=recorder)
        ready = threading.Event()
        event = MarketDataEvent(
            event_type=MarketDataEvent.TYPE_SETTLED_TRADE,
            pool_application='pool-app',
            pool_id=7,
            transaction_id=10,
        )

        async def consumer():
            ready.set()
            return await queue.get()

        task = asyncio.create_task(consumer())
        await asyncio.to_thread(ready.wait, 1)

        producer_thread = threading.Thread(target=lambda: queue.put_nowait(event))
        producer_thread.start()
        producer_thread.join(timeout=1)
        await asyncio.wait_for(task, timeout=0.2)

        self.assertEqual(recorder.records[0]['stage'], 'enqueue_threadsafe_scheduled')
        self.assertEqual(recorder.records[0]['event_type'], MarketDataEvent.TYPE_SETTLED_TRADE)
        self.assertEqual(recorder.records[0]['pool_id'], 7)

    async def test_put_nowait_sheds_oldest_when_queue_is_full(self):
        recorder = FakeDiagnosticRecorder()
        queue = MarketDataEventQueue(maxsize=1, diagnostic_recorder=recorder)
        old_event = MarketDataEvent(
            event_type=MarketDataEvent.TYPE_SETTLED_TRADE,
            pool_application='pool-app',
            transaction_id=1,
        )
        new_event = MarketDataEvent(
            event_type=MarketDataEvent.TYPE_SETTLED_TRADE,
            pool_application='pool-app',
            transaction_id=2,
        )

        queue.put_nowait(old_event)
        queue.put_nowait(new_event)

        self.assertEqual(await queue.get(), new_event)
        self.assertIn(
            'enqueue_shed_oldest',
            [record['stage'] for record in recorder.records],
        )


if __name__ == '__main__':
    unittest.main()
