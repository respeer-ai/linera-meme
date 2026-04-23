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

        async def ingest_until_caught_up(self, chain_id: str, *, max_blocks: int, mode: str = 'catch_up'):
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

    async def test_on_chain_notification_triggers_bounded_catch_up(self):
        runner = self.FakeCatchUpRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=20,
            allowed_chain_ids=('chain-a', 'chain-b'),
        )

        result = await processor.on_chain_notification('chain-a')

        self.assertEqual(runner.calls, [('chain-a', 20, 'catch_up')])
        self.assertEqual(result['trigger'], 'notification')
        self.assertTrue(result['accepted'])
        self.assertEqual(result['result']['chain_id'], 'chain-a')
        self.assertEqual(result['result']['ingested_count'], 1)
        self.assertEqual(result['result']['batch_count'], 1)

    async def test_on_chain_notification_ignores_unconfigured_chain(self):
        runner = self.FakeCatchUpRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=20,
            allowed_chain_ids=('chain-a',),
        )

        result = await processor.on_chain_notification('chain-z')

        self.assertEqual(runner.calls, [])
        self.assertFalse(result['accepted'])
        self.assertEqual(result['reason'], 'chain_not_configured')

    async def test_on_subscription_reconnect_triggers_bounded_catch_up(self):
        runner = self.FakeCatchUpRunner()
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=12,
            allowed_chain_ids=('chain-a',),
        )

        result = await processor.on_subscription_reconnect('chain-a')

        self.assertEqual(runner.calls, [('chain-a', 12, 'catch_up')])
        self.assertEqual(result['trigger'], 'reconnect_reconcile')
        self.assertTrue(result['accepted'])
        self.assertEqual(result['result']['batch_count'], 1)

    async def test_on_chain_notification_continues_until_caught_up(self):
        runner = self.FakeCatchUpRunner(results=[
            {'ingested_count': 20, 'caught_up': False},
            {'ingested_count': 7, 'caught_up': True},
        ])
        processor = ChainEventProcessor(
            catch_up_runner=runner,
            max_blocks_per_chain=20,
            allowed_chain_ids=('chain-a',),
        )

        result = await processor.on_chain_notification('chain-a')

        self.assertEqual(
            runner.calls,
            [
                ('chain-a', 20, 'catch_up'),
                ('chain-a', 20, 'catch_up'),
            ],
        )
        self.assertEqual(result['result']['ingested_count'], 27)
        self.assertEqual(result['result']['batch_count'], 2)
        self.assertTrue(result['result']['caught_up'])

    async def test_on_chain_notification_serializes_same_chain_processing(self):
        gate = asyncio.Event()
        release = asyncio.Event()

        class SerializedRunner:
            def __init__(self):
                self.calls = []

            async def ingest_until_caught_up(self, chain_id: str, *, max_blocks: int, mode: str = 'catch_up'):
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
        )

        first_task = asyncio.create_task(processor.on_chain_notification('chain-a'))
        await gate.wait()
        second_task = asyncio.create_task(processor.on_chain_notification('chain-a'))
        await asyncio.sleep(0)
        self.assertFalse(second_task.done())

        release.set()
        first_result, second_result = await asyncio.gather(first_task, second_task)

        self.assertEqual(runner.calls, [('chain-a', 5, 'catch_up'), ('chain-a', 5, 'catch_up')])
        self.assertEqual(first_result['result']['batch_count'], 1)
        self.assertEqual(second_result['result']['batch_count'], 1)
