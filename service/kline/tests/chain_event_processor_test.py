import asyncio
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from ingestion.chain_event_processor import ChainEventProcessor  # noqa: E402


class ChainEventProcessorTest(unittest.IsolatedAsyncioTestCase):
    class FakeCatchUpRunner:
        def __init__(self, results=None):
            self.calls = []
            self.results = list(results or [])

        async def ingest_until_caught_up(
            self,
            chain_id: str,
            *,
            max_blocks: int,
            mode: str = 'catch_up',
            drain_post_ingest=False,
        ):
            self.calls.append((chain_id, max_blocks, mode))
            if self.results:
                result = dict(self.results.pop(0))
                result.setdefault('chain_id', chain_id)
                result.setdefault('mode', mode)
                return result
            return {
                'chain_id': chain_id,
                'ingested_count': 1,
                'caught_up': True,
                'mode': mode,
            }

    class FakeRegistryRefresh:
        def __init__(self, result=None):
            self.calls = 0
            self.result = result

        async def __call__(self):
            self.calls += 1
            return self.result

    async def test_on_chain_notification_triggers_bounded_catch_up(self):
        runner = self.FakeCatchUpRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=20,
            allowed_chain_ids=('chain-a', 'chain-b'),
            retry_enabled=False,
        )

        result = await processor.on_chain_notification('chain-a')
        last_result = await processor.wait_for_idle('chain-a')

        self.assertEqual(runner.calls, [('chain-a', 20, 'catch_up')])
        self.assertEqual(result['trigger'], 'notification')
        self.assertTrue(result['accepted'])
        self.assertTrue(result['queued'])
        self.assertIsNone(result['registry_refresh'])
        self.assertEqual(last_result['chain_id'], 'chain-a')
        self.assertEqual(last_result['ingested_count'], 1)
        self.assertEqual(last_result['batch_count'], 1)

    async def test_on_chain_notification_ignores_unconfigured_chain(self):
        runner = self.FakeCatchUpRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=20,
            allowed_chain_ids=('chain-a',),
            retry_enabled=False,
        )

        result = await processor.on_chain_notification('chain-z')

        self.assertEqual(runner.calls, [])
        self.assertFalse(result['accepted'])
        self.assertEqual(result['reason'], 'chain_not_configured')
        self.assertIsNone(result['registry_refresh'])

    async def test_on_subscription_reconnect_triggers_bounded_catch_up(self):
        runner = self.FakeCatchUpRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=12,
            allowed_chain_ids=('chain-a',),
            retry_enabled=False,
        )

        result = await processor.on_subscription_reconnect('chain-a')
        last_result = await processor.wait_for_idle('chain-a')

        self.assertEqual(runner.calls, [('chain-a', 12, 'catch_up')])
        self.assertEqual(result['trigger'], 'reconnect_reconcile')
        self.assertTrue(result['accepted'])
        self.assertIsNone(result['registry_refresh'])
        self.assertEqual(last_result['batch_count'], 1)

    async def test_on_chain_notification_processes_one_bounded_batch(self):
        runner = self.FakeCatchUpRunner(results=[
            {'ingested_count': 20, 'caught_up': False},
            {'ingested_count': 7, 'caught_up': True},
        ])
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=20,
            allowed_chain_ids=('chain-a',),
            retry_enabled=False,
        )

        result = await processor.on_chain_notification('chain-a')
        last_result = await processor.wait_for_idle('chain-a')

        self.assertEqual(
            runner.calls,
            [
                ('chain-a', 20, 'catch_up'),
            ],
        )
        self.assertTrue(result['queued'])
        self.assertEqual(last_result['ingested_count'], 20)
        self.assertEqual(last_result['batch_count'], 1)
        self.assertFalse(last_result['caught_up'])

    async def test_on_chain_notification_schedules_retry_for_unfinished_batch(self):
        runner = self.FakeCatchUpRunner(results=[
            {'ingested_count': 20, 'caught_up': False},
            {'ingested_count': 7, 'caught_up': True},
        ])
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=20,
            allowed_chain_ids=('chain-a',),
            retry_delay_seconds=0.001,
        )

        result = await processor.on_chain_notification('chain-a')
        await asyncio.sleep(0.02)
        last_result = await processor.wait_for_idle('chain-a')

        self.assertTrue(result['queued'])
        self.assertTrue(last_result['caught_up'])
        self.assertEqual(
            runner.calls,
            [
                ('chain-a', 20, 'catch_up'),
                ('chain-a', 20, 'catch_up'),
            ],
        )

    async def test_on_chain_notification_serializes_same_chain_processing(self):
        gate = asyncio.Event()
        release = asyncio.Event()

        class SerializedRunner:
            def __init__(self):
                self.calls = []

            async def ingest_until_caught_up(
                self,
                chain_id: str,
                *,
                max_blocks: int,
                mode: str = 'catch_up',
                drain_post_ingest=False,
            ):
                self.calls.append((chain_id, max_blocks, mode))
                if len(self.calls) == 1:
                    gate.set()
                    await release.wait()
                return {
                    'chain_id': chain_id,
                    'ingested_count': 1,
                    'caught_up': True,
                    'mode': mode,
                }

        runner = SerializedRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=5,
            allowed_chain_ids=('chain-a',),
            retry_enabled=False,
        )

        first_task = asyncio.create_task(processor.on_chain_notification('chain-a'))
        second_task = asyncio.create_task(processor.on_chain_notification('chain-a'))
        first_result, second_result = await asyncio.gather(first_task, second_task)
        await gate.wait()

        release.set()
        last_result = await processor.wait_for_idle('chain-a')

        self.assertEqual(runner.calls, [('chain-a', 5, 'catch_up')])
        self.assertTrue(first_result['queued'])
        self.assertFalse(second_result['queued'])
        self.assertEqual(last_result['batch_count'], 1)

    async def test_add_chain_ids_allows_new_chain_notifications(self):
        runner = self.FakeCatchUpRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=9,
            allowed_chain_ids=('chain-a',),
            retry_enabled=False,
        )

        processor.add_chain_ids(('chain-b',))
        result = await processor.on_chain_notification('chain-b')
        last_result = await processor.wait_for_idle('chain-b')

        self.assertTrue(result['accepted'])
        self.assertEqual(last_result['chain_id'], 'chain-b')
        self.assertEqual(runner.calls, [('chain-b', 9, 'catch_up')])

    async def test_notification_refreshes_registry_before_allowed_check(self):
        runner = self.FakeCatchUpRunner()
        refresh = self.FakeRegistryRefresh(result=('chain-b',))
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=9,
            allowed_chain_ids=('chain-a',),
            registry_refresh=refresh,
            retry_enabled=False,
        )

        async def refresh_and_enroll():
            await refresh()
            processor.add_chain_ids(('chain-b',))
            return ('chain-b',)

        processor.registry_refresh = refresh_and_enroll
        result = await processor.on_chain_notification('chain-b')
        await processor.wait_for_idle('chain-b')

        self.assertEqual(refresh.calls, 1)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['registry_refresh'], ('chain-b',))
        self.assertEqual(runner.calls, [('chain-b', 9, 'catch_up')])

    async def test_on_chain_notification_times_out_one_bounded_task(self):
        class HangingRunner:
            async def ingest_until_caught_up(self, chain_id: str, *, max_blocks: int, mode: str = 'catch_up', drain_post_ingest=False):
                await asyncio.sleep(1)

        processor = ChainEventProcessor(
            catch_up_runner=HangingRunner(),
            max_blocks_per_chain=9,
            allowed_chain_ids=('chain-a',),
            task_timeout_seconds=0.01,
            retry_enabled=False,
        )

        result = await processor.on_chain_notification('chain-a')
        last_result = await processor.wait_for_idle('chain-a')

        self.assertTrue(result['queued'])
        self.assertTrue(last_result['timed_out'])
        self.assertFalse(last_result['caught_up'])
        self.assertEqual(last_result['batch_count'], 0)

    async def test_timed_out_task_does_not_retry_without_new_notification(self):
        class HangingRunner:
            def __init__(self):
                self.calls = 0

            async def ingest_until_caught_up(self, chain_id: str, *, max_blocks: int, mode: str = 'catch_up', drain_post_ingest=False):
                self.calls += 1
                await asyncio.sleep(1)

        runner = HangingRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=9,
            allowed_chain_ids=('chain-a',),
            task_timeout_seconds=0.01,
            retry_delay_seconds=0.001,
        )

        await processor.on_chain_notification('chain-a')
        await processor.wait_for_idle('chain-a')
        await asyncio.sleep(0.02)

        self.assertEqual(runner.calls, 1)

    async def test_failed_task_is_recorded_and_retried(self):
        class FlakyRunner:
            def __init__(self):
                self.calls = 0

            async def ingest_until_caught_up(self, chain_id: str, *, max_blocks: int, mode: str = 'catch_up', drain_post_ingest=False):
                self.calls += 1
                if self.calls == 1:
                    raise RuntimeError('temporary failure')
                return {
                    'chain_id': chain_id,
                    'ingested_count': 1,
                    'caught_up': True,
                    'mode': mode,
                }

        runner = FlakyRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=9,
            allowed_chain_ids=('chain-a',),
            retry_delay_seconds=0.001,
        )

        await processor.on_chain_notification('chain-a')
        await asyncio.sleep(0.02)
        last_result = await processor.wait_for_idle('chain-a')

        self.assertEqual(runner.calls, 2)
        self.assertTrue(last_result['caught_up'])
