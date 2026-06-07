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
                    'settled_outputs': [self._settled_output(item)],
                }
                for item in items
            ]

        def _settled_output(self, item):
            output = {'settled_output_type': 'settled_trade'}
            if item.get('pool_application_id') is not None:
                output['pool_application_id'] = item['pool_application_id']
            return output

    class FakeBusinessFreshnessService:
        def __init__(self, should_fail=False):
            self.should_fail = should_fail
            self.calls = []

        def check(self, *, chain_id=None, pool_application=None, trigger=None):
            self.calls.append((chain_id, pool_application, trigger))
            if self.should_fail:
                raise RuntimeError('freshness failed')
            return {'status': 'fresh'}

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
            partition_key='raw_events',
        )

        self.assertEqual(result['processed_count'], 2)
        self.assertEqual(result['derived_output_count'], 2)
        self.assertEqual(result['last_sequence'], '11')
        self.assertEqual(result['last_block_hash'], 'block-2')
        self.assertEqual(cursor_repo.attempts[0]['cursor_scope'], 'derive')
        self.assertEqual(cursor_repo.successes[0]['partition_key'], 'raw_events')
        self.assertEqual(cursor_repo.failures, [])

    def test_process_items_checks_business_freshness_for_distinct_pools(self):
        cursor_repo = self.FakeProcessingCursorRepository()
        freshness_service = self.FakeBusinessFreshnessService()
        worker = MarketDerivationWorker(
            settled_market_materializer=self.FakeSettledMarketMaterializer(),
            processing_cursor_repository=cursor_repo,
            business_freshness_service=freshness_service,
        )

        worker.process_items([
            {'normalized_event_id': 'event-1', 'pool_application_id': 'pool-a'},
            {'normalized_event_id': 'event-2', 'pool_application_id': 'pool-a'},
            {'normalized_event_id': 'event-3', 'pool_application_id': 'pool-b'},
        ])

        self.assertEqual(
            freshness_service.calls,
            [
                (None, 'pool-a', 'market_derivation'),
                (None, 'pool-b', 'market_derivation'),
            ],
        )

    def test_process_items_checks_global_business_freshness_without_pool_outputs(self):
        cursor_repo = self.FakeProcessingCursorRepository()
        freshness_service = self.FakeBusinessFreshnessService()
        worker = MarketDerivationWorker(
            settled_market_materializer=self.FakeSettledMarketMaterializer(),
            processing_cursor_repository=cursor_repo,
            business_freshness_service=freshness_service,
        )

        worker.process_items([{'normalized_event_id': 'event-1'}])

        self.assertEqual(freshness_service.calls, [(None, None, 'market_derivation')])

    def test_business_freshness_failure_does_not_block_process_result(self):
        cursor_repo = self.FakeProcessingCursorRepository()
        freshness_service = self.FakeBusinessFreshnessService(should_fail=True)
        worker = MarketDerivationWorker(
            settled_market_materializer=self.FakeSettledMarketMaterializer(),
            processing_cursor_repository=cursor_repo,
            business_freshness_service=freshness_service,
        )

        result = worker.process_items([
            {'normalized_event_id': 'event-1', 'pool_application_id': 'pool-a'},
        ])

        self.assertEqual(result['processed_count'], 1)
        self.assertEqual(cursor_repo.failures, [])
        self.assertEqual(freshness_service.calls, [(None, 'pool-a', 'market_derivation')])

    def test_materializer_failure_does_not_check_business_freshness(self):
        cursor_repo = self.FakeProcessingCursorRepository()
        freshness_service = self.FakeBusinessFreshnessService()
        worker = MarketDerivationWorker(
            settled_market_materializer=self.FakeSettledMarketMaterializer(should_fail=True),
            processing_cursor_repository=cursor_repo,
            business_freshness_service=freshness_service,
        )

        with self.assertRaisesRegex(RuntimeError, 'derivation failed'):
            worker.process_items([{'normalized_event_id': 'event-1'}])

        self.assertEqual(freshness_service.calls, [])

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
