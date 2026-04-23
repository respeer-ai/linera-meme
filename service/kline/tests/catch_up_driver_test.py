import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from ingestion.catch_up_driver import CatchUpDriver  # noqa: E402


class CatchUpDriverTest(unittest.IsolatedAsyncioTestCase):
    class FakeCatchUpRunner:
        def __init__(self):
            self.calls = []

        async def ingest_until_caught_up(self, chain_id: str, *, max_blocks: int, mode: str = 'catch_up'):
            self.calls.append((chain_id, max_blocks, mode))
            return {
                'chain_id': chain_id,
                'mode': mode,
                'ingested_count': 2 if chain_id == 'chain-a' else 1,
                'caught_up': True,
            }

    async def test_run_once_executes_each_chain_and_aggregates_counts(self):
        runner = self.FakeCatchUpRunner()
        driver = CatchUpDriver(
            catch_up_runner=runner,
            chain_ids=('chain-a', 'chain-b'),
            max_blocks_per_chain=10,
        )

        result = await driver.run_once()

        self.assertEqual(
            runner.calls,
            [
                ('chain-a', 10, 'catch_up'),
                ('chain-b', 10, 'catch_up'),
            ],
        )
        self.assertEqual(result['chain_ids'], ['chain-a', 'chain-b'])
        self.assertEqual(result['chain_count'], 2)
        self.assertEqual(result['max_blocks_per_chain'], 10)
        self.assertEqual(result['total_ingested_count'], 3)
