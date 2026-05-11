import asyncio
import sys
import threading
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from realtime.candle_finality_scheduler import CandleFinalityScheduler  # noqa: E402


class FakeAccountCodec:
    def format_account(self, *, chain_id, owner):
        return f'{owner}@{chain_id}'


class CandleFinalitySchedulerTest(unittest.IsolatedAsyncioTestCase):
    async def test_emit_runs_outside_event_loop_thread(self):
        loop_thread = threading.get_ident()
        emit_thread = None

        class Repository:
            def list_current_pool_views(self):
                nonlocal emit_thread
                emit_thread = threading.get_ident()
                return []

        scheduler = CandleFinalityScheduler(
            queue=asyncio.Queue(),
            pool_catalog_repository=Repository(),
            account_codec=FakeAccountCodec(),
        )

        await scheduler._emit_due_events_async()
        scheduler.stop()

        self.assertIsNotNone(emit_thread)
        self.assertNotEqual(loop_thread, emit_thread)

    async def test_emit_timeout_does_not_block_next_cycle_forever(self):
        gate = threading.Event()

        class Repository:
            def list_current_pool_views(self):
                gate.wait(timeout=1)
                return []

        scheduler = CandleFinalityScheduler(
            queue=asyncio.Queue(),
            pool_catalog_repository=Repository(),
            account_codec=FakeAccountCodec(),
            emit_timeout_seconds=0.01,
        )

        started_at = time.time()
        await scheduler._emit_due_events_async()
        elapsed = time.time() - started_at
        scheduler.stop()
        gate.set()

        self.assertLess(elapsed, 0.2)

    async def test_timeout_recovers_next_emit_without_waiting_for_stuck_thread(self):
        gate = threading.Event()
        calls = 0
        closed = 0

        class Repository:
            def list_current_pool_views(self):
                nonlocal calls
                calls += 1
                gate.wait(timeout=1)
                return []

            def close(self):
                nonlocal closed
                closed += 1

        scheduler = CandleFinalityScheduler(
            queue=asyncio.Queue(),
            pool_catalog_repository=Repository(),
            pool_catalog_repository_factory=lambda: Repository(),
            account_codec=FakeAccountCodec(),
            emit_timeout_seconds=0.01,
        )

        await scheduler._emit_due_events_async()
        await scheduler._emit_due_events_async()
        self.assertEqual(calls, 2)

        gate.set()
        for _ in range(20):
            if closed >= 1:
                break
            await asyncio.sleep(0.01)
        scheduler.stop()

        self.assertEqual(calls, 2)
        self.assertGreaterEqual(closed, 1)

    async def test_uses_thread_local_repository_factory(self):
        class Repository:
            def __init__(self, label):
                self.label = label
                self.calls = 0
                self.closed = False

            def list_current_pool_views(self):
                self.calls += 1
                return []

            def close(self):
                self.closed = True

        main_repository = Repository('main')
        worker_repository = Repository('worker')
        scheduler = CandleFinalityScheduler(
            queue=asyncio.Queue(),
            pool_catalog_repository=main_repository,
            pool_catalog_repository_factory=lambda: worker_repository,
            account_codec=FakeAccountCodec(),
        )

        await scheduler._emit_due_events_async()
        scheduler.stop()

        self.assertEqual(main_repository.calls, 0)
        self.assertEqual(worker_repository.calls, 1)
        self.assertTrue(worker_repository.closed)


if __name__ == '__main__':
    unittest.main()
