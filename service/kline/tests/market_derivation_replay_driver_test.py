import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.market_derivation_replay_driver import MarketDerivationReplayDriver  # noqa: E402


class MarketDerivationReplayDriverTest(unittest.TestCase):
    class FakeNormalizedEventRepository:
        def __init__(self):
            self.calls = []
            self.items_by_table = {}

        def list_market_derivation_candidates(self, *, raw_table, after_sequence, limit):
            self.calls.append((raw_table, after_sequence, limit))
            return list(self.items_by_table.get(raw_table, []))[:limit]

    class FakeProcessingCursorRepository:
        def __init__(self, cursor=None):
            self.loaded_cursor = cursor
            self.calls = []

        def load_cursor(self, *, cursor_name, partition_key):
            self.calls.append((cursor_name, partition_key))
            return self.loaded_cursor

    class FakeMarketDerivationWorker:
        def __init__(self, cursor_repository=None):
            self.cursor_name = 'layer3_market_deriver'
            self.cursor_repository = cursor_repository
            self.calls = []

        def process_items(self, items, *, partition_key, reprocess_reason=None):
            self.calls.append((items, partition_key, reprocess_reason))
            if self.cursor_repository is not None:
                self.cursor_repository.loaded_cursor = {'last_sequence': items[-1]['raw_fact_id']}
            return {
                'processed_count': len(items),
                'derived_output_count': len(items),
                'last_sequence': items[-1]['raw_fact_id'],
                'last_block_hash': items[-1].get('target_block_hash'),
            }

    def test_run_once_uses_cursor_sequence_and_processes_candidates(self):
        repository = self.FakeNormalizedEventRepository()
        repository.items_by_table['raw_posted_messages'] = [
            {
                'normalized_event_id': 'event-8',
                'raw_fact_id': '8',
                'target_block_hash': 'block-8',
            },
        ]
        driver = MarketDerivationReplayDriver(
            normalized_event_repository=repository,
            processing_cursor_repository=self.FakeProcessingCursorRepository({'last_sequence': '7'}),
            market_derivation_worker=self.FakeMarketDerivationWorker(),
        )

        result = driver.run_once(
            raw_table='raw_posted_messages',
            reprocess_reason='manual',
        )

        self.assertEqual(repository.calls[0], ('raw_posted_messages', 7, 100))
        self.assertEqual(result['processed_count'], 1)
        self.assertEqual(result['derived_output_count'], 1)
        self.assertTrue(result['caught_up'])

    def test_run_until_caught_up_runs_multiple_batches(self):
        class SequencedRepository(self.FakeNormalizedEventRepository):
            def __init__(self):
                super().__init__()
                self.responses = {
                    ('raw_posted_messages', None): [{'normalized_event_id': 'event-1', 'raw_fact_id': '1'}],
                    ('raw_posted_messages', 1): [],
                }

            def list_market_derivation_candidates(self, *, raw_table, after_sequence, limit):
                self.calls.append((raw_table, after_sequence, limit))
                return list(self.responses.get((raw_table, after_sequence), []))

        repository = SequencedRepository()
        cursor_repository = self.FakeProcessingCursorRepository()
        worker = self.FakeMarketDerivationWorker(cursor_repository)
        driver = MarketDerivationReplayDriver(
            normalized_event_repository=repository,
            processing_cursor_repository=cursor_repository,
            market_derivation_worker=worker,
        )

        result = driver.run_until_caught_up(
            raw_table='raw_posted_messages',
            batch_limit=1,
            max_batches=3,
        )

        self.assertEqual(result['batch_count'], 2)
        self.assertEqual(result['processed_count'], 1)
        self.assertEqual(result['derived_output_count'], 1)
        self.assertTrue(result['caught_up'])

    def test_run_all_until_caught_up_drains_all_configured_tables(self):
        class SequencedRepository(self.FakeNormalizedEventRepository):
            def __init__(self):
                super().__init__()
                self.responses = {
                    ('raw_posted_messages', None): [
                        {'normalized_event_id': 'event-1', 'raw_fact_id': '1'},
                    ],
                    ('raw_posted_messages', 1): [],
                }

            def list_market_derivation_candidates(self, *, raw_table, after_sequence, limit):
                self.calls.append((raw_table, after_sequence, limit))
                return list(self.responses.get((raw_table, after_sequence), []))

        repository = SequencedRepository()
        cursor_repository = self.FakeProcessingCursorRepository()
        worker = self.FakeMarketDerivationWorker(cursor_repository)
        driver = MarketDerivationReplayDriver(
            normalized_event_repository=repository,
            processing_cursor_repository=cursor_repository,
            market_derivation_worker=worker,
            batch_limit=1,
        )

        result = driver.run_all_until_caught_up(reprocess_reason='post_ingest')

        self.assertEqual(result['table_count'], 1)
        self.assertEqual(result['processed_count'], 1)
        self.assertEqual(result['derived_output_count'], 1)
        self.assertTrue(result['caught_up'])
