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


from ingestion.catch_up_runner import CatchUpRunner  # noqa: E402
from ingestion.cursors import ChainCursor  # noqa: E402
from integration.block_not_available_error import BlockNotAvailableError  # noqa: E402


class CatchUpRunnerTest(unittest.IsolatedAsyncioTestCase):
    class FakeChainCursorStore:
        def __init__(self, cursor):
            self.cursor = cursor
            self.calls = []

        def load(self, chain_id: str):
            self.calls.append(chain_id)
            return self.cursor

    class FakeCoordinator:
        def __init__(self, results=None):
            self.calls = []
            self.results = list(results or [])

        async def ingest_from_cursor(self, cursor, mode: str = 'catch_up'):
            self.calls.append((cursor, mode))
            if self.results:
                result = self.results.pop(0)
                if isinstance(result, Exception):
                    raise result
                return result
            return {
                'chain_id': cursor.chain_id,
                'height': 8,
                'ingest_status': 'ingested',
            }

    class FakePostIngestPipeline:
        def __init__(self, delay_seconds=0):
            self.calls = []
            self.bounded_calls = []
            self.delay_seconds = delay_seconds
            self.thread_ids = []

        def run_until_caught_up(self, *, reprocess_reason=None):
            self.thread_ids.append(threading.get_ident())
            if self.delay_seconds:
                time.sleep(self.delay_seconds)
            self.calls.append(reprocess_reason)
            return {
                'reprocess_reason': reprocess_reason,
                'normalization': {'caught_up': True},
                'market_derivation': {'caught_up': True},
            }

        def run_bounded(self, *, reprocess_reason=None):
            self.thread_ids.append(threading.get_ident())
            if self.delay_seconds:
                time.sleep(self.delay_seconds)
            self.bounded_calls.append(reprocess_reason)
            return {
                'reprocess_reason': reprocess_reason,
                'normalization': {'caught_up': True},
                'market_derivation': {'caught_up': True},
                'caught_up': True,
            }

        def close(self):
            self.closed = True

    async def test_ingest_next_loads_cursor_and_advances_one_step(self):
        store = self.FakeChainCursorStore(
            ChainCursor(
                chain_id='chain-a',
                last_finalized_height=7,
                last_finalized_block_hash='hash-7',
            )
        )
        coordinator = self.FakeCoordinator()
        runner = CatchUpRunner(store, coordinator)

        result = await runner.ingest_next('chain-a')

        self.assertEqual(store.calls, ['chain-a'])
        self.assertEqual(coordinator.calls[0][0].chain_id, 'chain-a')
        self.assertEqual(coordinator.calls[0][0].last_finalized_height, 7)
        self.assertEqual(coordinator.calls[0][1], 'catch_up')
        self.assertEqual(result['height'], 8)

    async def test_ingest_until_caught_up_stops_when_block_not_available(self):
        store = self.FakeChainCursorStore(
            ChainCursor(
                chain_id='chain-a',
                last_finalized_height=7,
                last_finalized_block_hash='hash-7',
            )
        )
        coordinator = self.FakeCoordinator(results=[
            {'chain_id': 'chain-a', 'height': 8, 'ingest_status': 'ingested'},
            {'chain_id': 'chain-a', 'height': 9, 'ingest_status': 'ingested'},
            BlockNotAvailableError('tip height is 9'),
        ])
        runner = CatchUpRunner(store, coordinator)

        result = await runner.ingest_until_caught_up('chain-a', max_blocks=5)

        self.assertEqual(store.calls, ['chain-a', 'chain-a', 'chain-a'])
        self.assertEqual(len(coordinator.calls), 3)
        self.assertEqual(result['ingested_count'], 2)
        self.assertTrue(result['caught_up'])
        self.assertEqual(
            result['ingested'],
            [
                {'chain_id': 'chain-a', 'height': 8, 'ingest_status': 'ingested'},
                {'chain_id': 'chain-a', 'height': 9, 'ingest_status': 'ingested'},
            ],
        )

    async def test_ingest_until_caught_up_respects_max_blocks_limit(self):
        store = self.FakeChainCursorStore(ChainCursor(chain_id='chain-a'))
        coordinator = self.FakeCoordinator(results=[
            {'chain_id': 'chain-a', 'height': 0, 'ingest_status': 'ingested'},
            {'chain_id': 'chain-a', 'height': 1, 'ingest_status': 'ingested'},
            {'chain_id': 'chain-a', 'height': 2, 'ingest_status': 'ingested'},
        ])
        runner = CatchUpRunner(store, coordinator)

        result = await runner.ingest_until_caught_up('chain-a', max_blocks=2)

        self.assertEqual(len(coordinator.calls), 2)
        self.assertEqual(result['ingested_count'], 2)
        self.assertFalse(result['caught_up'])

    async def test_ingest_until_caught_up_runs_post_ingest_pipeline_after_ingesting_blocks(self):
        store = self.FakeChainCursorStore(ChainCursor(chain_id='chain-a'))
        coordinator = self.FakeCoordinator(results=[
            {'chain_id': 'chain-a', 'height': 0, 'ingest_status': 'ingested'},
            BlockNotAvailableError('tip height is 0'),
        ])
        pipeline = self.FakePostIngestPipeline()
        runner = CatchUpRunner(
            store,
            coordinator,
            post_ingest_pipeline=pipeline,
        )

        result = await runner.ingest_until_caught_up('chain-a', max_blocks=5, mode='live')

        self.assertEqual(pipeline.bounded_calls, ['live:chain-a'])
        self.assertEqual(
            result['post_ingest_result'],
            {
                'reprocess_reason': 'live:chain-a',
                'normalization': {'caught_up': True},
                'market_derivation': {'caught_up': True},
                'caught_up': True,
            },
        )

    async def test_ingest_until_caught_up_skips_post_ingest_pipeline_when_nothing_new_was_ingested(self):
        store = self.FakeChainCursorStore(ChainCursor(chain_id='chain-a'))
        coordinator = self.FakeCoordinator(results=[
            BlockNotAvailableError('tip height is 0'),
        ])
        pipeline = self.FakePostIngestPipeline()
        runner = CatchUpRunner(
            store,
            coordinator,
            post_ingest_pipeline=pipeline,
        )

        result = await runner.ingest_until_caught_up('chain-a', max_blocks=5)

        self.assertEqual(pipeline.bounded_calls, [])
        self.assertIsNone(result['post_ingest_result'])

    async def test_ingest_until_caught_up_can_create_post_ingest_pipeline_in_worker_thread(self):
        store = self.FakeChainCursorStore(ChainCursor(chain_id='chain-a'))
        coordinator = self.FakeCoordinator(results=[
            {'chain_id': 'chain-a', 'height': 0, 'ingest_status': 'ingested'},
            BlockNotAvailableError('tip height is 0'),
        ])
        created = []

        def factory():
            pipeline = self.FakePostIngestPipeline()
            pipeline.closed = False
            created.append(pipeline)
            return pipeline

        runner = CatchUpRunner(
            store,
            coordinator,
            post_ingest_pipeline_factory=factory,
        )

        result = await runner.ingest_until_caught_up('chain-a', max_blocks=5, mode='live')

        self.assertEqual(len(created), 1)
        self.assertEqual(created[0].bounded_calls, ['live:chain-a'])
        self.assertTrue(created[0].closed)
        self.assertTrue(result['post_ingest_result']['caught_up'])


    async def test_ingest_until_caught_up_can_drain_post_ingest_for_admin_repair(self):
        store = self.FakeChainCursorStore(ChainCursor(chain_id='chain-a'))
        coordinator = self.FakeCoordinator(results=[
            {'chain_id': 'chain-a', 'height': 0, 'ingest_status': 'ingested'},
            BlockNotAvailableError('tip height is 0'),
        ])
        pipeline = self.FakePostIngestPipeline()
        runner = CatchUpRunner(
            store,
            coordinator,
            post_ingest_pipeline=pipeline,
        )

        result = await runner.ingest_until_caught_up(
            'chain-a',
            max_blocks=5,
            drain_post_ingest=True,
        )

        self.assertEqual(pipeline.calls, ['catch_up:chain-a'])
        self.assertEqual(pipeline.bounded_calls, [])
        self.assertEqual(result['post_ingest_result']['reprocess_reason'], 'catch_up:chain-a')

    async def test_ingest_until_caught_up_does_not_block_event_loop_while_post_ingest_runs(self):
        store = self.FakeChainCursorStore(ChainCursor(chain_id='chain-a'))
        coordinator = self.FakeCoordinator(results=[
            {'chain_id': 'chain-a', 'height': 0, 'ingest_status': 'ingested'},
            BlockNotAvailableError('tip height is 0'),
        ])
        pipeline = self.FakePostIngestPipeline(delay_seconds=0.05)
        runner = CatchUpRunner(
            store,
            coordinator,
            post_ingest_pipeline=pipeline,
        )
        main_thread_id = threading.get_ident()
        task = asyncio.create_task(
            runner.ingest_until_caught_up('chain-a', max_blocks=5)
        )

        await asyncio.sleep(0.01)
        loop_was_not_blocked = not task.done()
        result = await task

        self.assertTrue(loop_was_not_blocked)
        self.assertEqual(result['post_ingest_result']['reprocess_reason'], 'catch_up:chain-a')
        self.assertNotEqual(pipeline.thread_ids, [])
        self.assertNotEqual(pipeline.thread_ids[0], main_thread_id)

    async def test_ingest_until_caught_up_does_not_stack_post_ingest_threads(self):
        store = self.FakeChainCursorStore(ChainCursor(chain_id='chain-a'))
        coordinator = self.FakeCoordinator(results=[
            {'chain_id': 'chain-a', 'height': 0, 'ingest_status': 'ingested'},
            BlockNotAvailableError('tip height is 0'),
            {'chain_id': 'chain-a', 'height': 1, 'ingest_status': 'ingested'},
            BlockNotAvailableError('tip height is 1'),
        ])
        pipeline = self.FakePostIngestPipeline(delay_seconds=0.05)
        runner = CatchUpRunner(
            store,
            coordinator,
            post_ingest_pipeline=pipeline,
        )

        first_task = asyncio.create_task(
            runner.ingest_until_caught_up('chain-a', max_blocks=5)
        )
        await asyncio.sleep(0.01)
        second_result = await runner.ingest_until_caught_up('chain-a', max_blocks=5)
        first_result = await first_task

        self.assertEqual(first_result['post_ingest_result']['reprocess_reason'], 'catch_up:chain-a')
        self.assertEqual(second_result['post_ingest_result']['reason'], 'post_ingest_in_flight')
        self.assertEqual(len(pipeline.thread_ids), 1)

    async def test_post_ingest_timeout_recovers_next_run(self):
        store = self.FakeChainCursorStore(ChainCursor(chain_id='chain-a'))
        coordinator = self.FakeCoordinator(results=[
            {'chain_id': 'chain-a', 'height': 0, 'ingest_status': 'ingested'},
            BlockNotAvailableError('tip height is 0'),
            {'chain_id': 'chain-a', 'height': 1, 'ingest_status': 'ingested'},
            BlockNotAvailableError('tip height is 1'),
        ])
        pipeline = self.FakePostIngestPipeline(delay_seconds=0.2)
        runner = CatchUpRunner(
            store,
            coordinator,
            post_ingest_pipeline=pipeline,
            post_ingest_timeout_seconds=0.01,
        )

        started_at = time.time()
        first_result = await runner.ingest_until_caught_up('chain-a', max_blocks=5)
        elapsed = time.time() - started_at
        second_result = await runner.ingest_until_caught_up('chain-a', max_blocks=5)
        runner.shutdown()

        self.assertLess(elapsed, 0.2)
        self.assertTrue(first_result['post_ingest_result']['timed_out'])
        self.assertTrue(second_result['post_ingest_result']['timed_out'])
        self.assertGreaterEqual(len(pipeline.thread_ids), 2)
