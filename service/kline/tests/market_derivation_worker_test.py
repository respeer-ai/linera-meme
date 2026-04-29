import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.market_derivation_worker import MarketDerivationWorker  # noqa: E402


class MarketDerivationWorkerTest(unittest.TestCase):
    class FakeSettledMarketMaterializer:
        def __init__(self, should_fail=False):
            self.should_fail = should_fail
            self.calls = []

        def materialize_batch(self, items):
            self.calls.append(items)
            if self.should_fail:
                raise RuntimeError('derivation failed')
            return [
                {
                    'normalized_event_id': item['normalized_event_id'],
                    'settled_outputs': [{'settled_output_type': 'settled_trade'}],
                }
                for item in items
            ]

    class FakeProcessingCursorRepository:
        def __init__(self):
            self.attempts = []
            self.successes = []
            self.failures = []

        def mark_attempt(self, **kwargs):
            self.attempts.append(kwargs)

        def mark_success(self, **kwargs):
            self.successes.append(kwargs)

        def mark_failure(self, **kwargs):
            self.failures.append(kwargs)

    def test_process_items_advances_layer3_cursor(self):
        cursor_repo = self.FakeProcessingCursorRepository()
        worker = MarketDerivationWorker(
            settled_market_materializer=self.FakeSettledMarketMaterializer(),
            processing_cursor_repository=cursor_repo,
        )

        result = worker.process_items(
            [
                {
                    'normalized_event_id': 'event-1',
                    'raw_fact_id': '10',
                    'target_block_hash': 'block-1',
                },
                {
                    'normalized_event_id': 'event-2',
                    'raw_fact_id': '11',
                    'target_block_hash': 'block-2',
                },
            ],
            partition_key='raw_posted_messages',
        )

        self.assertEqual(result['processed_count'], 2)
        self.assertEqual(result['derived_output_count'], 2)
        self.assertEqual(result['last_sequence'], '11')
        self.assertEqual(result['last_block_hash'], 'block-2')
        self.assertEqual(cursor_repo.attempts[0]['cursor_scope'], 'derive')
        self.assertEqual(cursor_repo.successes[0]['partition_key'], 'raw_posted_messages')
        self.assertEqual(cursor_repo.failures, [])

    def test_process_items_marks_failure_when_materializer_raises(self):
        cursor_repo = self.FakeProcessingCursorRepository()
        worker = MarketDerivationWorker(
            settled_market_materializer=self.FakeSettledMarketMaterializer(should_fail=True),
            processing_cursor_repository=cursor_repo,
        )

        with self.assertRaisesRegex(RuntimeError, 'derivation failed'):
            worker.process_items(
                [
                    {
                        'normalized_event_id': 'event-1',
                        'raw_fact_id': '10',
                        'target_block_hash': 'block-1',
                    },
                ]
            )

        self.assertEqual(len(cursor_repo.attempts), 1)
        self.assertEqual(len(cursor_repo.failures), 1)
        self.assertEqual(cursor_repo.successes, [])
