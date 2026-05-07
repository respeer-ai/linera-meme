import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from normalizer.normalization_replay_driver import NormalizationReplayDriver  # noqa: E402


class NormalizationReplayDriverTest(unittest.TestCase):
    class FakeRawRepository:
        def __init__(self):
            self.calls = []
            self.items_by_table = {}

        def list_normalization_candidates(self, *, raw_table, after_sequence, limit):
            self.calls.append((raw_table, after_sequence, limit))
            return list(self.items_by_table.get(raw_table, []))[:limit]

    class FakeProcessingCursorRepository:
        def __init__(self, cursor=None):
            self.cursor = cursor
            self.calls = []
            self.loaded_cursor = cursor

        def load_cursor(self, *, cursor_name, partition_key):
            self.calls.append((cursor_name, partition_key))
            return self.loaded_cursor

    class FakeNormalizationWorker:
        def __init__(self, cursor_repository=None):
            self.cursor_name = 'layer2_normalizer'
            self.calls = []
            self.cursor_repository = cursor_repository

        def process_items(self, items, *, partition_key, reprocess_reason=None):
            self.calls.append((items, partition_key, reprocess_reason))
            if self.cursor_repository is not None:
                self.cursor_repository.loaded_cursor = {
                    'last_sequence': items[-1]['raw_fact_id']
                }
            return {
                'processed_count': len(items),
                'normalized_event_count': len(items),
                'last_sequence': items[-1]['raw_fact_id'],
                'last_block_hash': items[-1].get('target_block_hash'),
            }

    def test_run_once_uses_cursor_sequence_and_processes_one_table(self):
        raw_repository = self.FakeRawRepository()
        raw_repository.items_by_table['raw_operations'] = [
            {
                'raw_fact_id': '8',
                'application_id': 'app-1',
                'payload_kind': 'operation',
                'target_block_hash': 'block-8',
            },
        ]
        driver = NormalizationReplayDriver(
            raw_repository=raw_repository,
            processing_cursor_repository=self.FakeProcessingCursorRepository(
                {'last_sequence': '7'}
            ),
            normalization_worker=self.FakeNormalizationWorker(),
        )

        result = driver.run_once(
            raw_table='raw_operations',
            reprocess_reason='registry_updated',
        )

        self.assertEqual(raw_repository.calls[0], ('raw_operations', 7, 100))
        self.assertEqual(result['processed_count'], 1)
        self.assertTrue(result['caught_up'])

    def test_run_once_returns_caught_up_when_no_items(self):
        driver = NormalizationReplayDriver(
            raw_repository=self.FakeRawRepository(),
            processing_cursor_repository=self.FakeProcessingCursorRepository(),
            normalization_worker=self.FakeNormalizationWorker(),
        )

        result = driver.run_once(raw_table='raw_posted_messages')

        self.assertEqual(result['processed_count'], 0)
        self.assertTrue(result['caught_up'])

    def test_run_all_iterates_configured_tables(self):
        raw_repository = self.FakeRawRepository()
        raw_repository.items_by_table['raw_operations'] = [
            {'raw_fact_id': '1', 'application_id': 'app-1', 'payload_kind': 'operation'},
        ]
        raw_repository.items_by_table['raw_posted_messages'] = [
            {'raw_fact_id': '2', 'application_id': 'app-2', 'payload_kind': 'message'},
        ]
        raw_repository.items_by_table['raw_events'] = [
            {'raw_fact_id': '3', 'application_id': 'app-3', 'payload_kind': 'event'},
        ]
        driver = NormalizationReplayDriver(
            raw_repository=raw_repository,
            processing_cursor_repository=self.FakeProcessingCursorRepository(),
            normalization_worker=self.FakeNormalizationWorker(),
        )

        result = driver.run_all()

        self.assertEqual(result['table_count'], 3)
        self.assertEqual(result['processed_count'], 3)

    def test_run_until_caught_up_runs_multiple_batches(self):
        class SequencedRawRepository(self.FakeRawRepository):
            def __init__(self):
                super().__init__()
                self.responses = {
                    ('raw_operations', None): [
                        {'raw_fact_id': '1', 'application_id': 'app-1', 'payload_kind': 'operation'},
                    ],
                    ('raw_operations', 1): [],
                }

            def list_normalization_candidates(self, *, raw_table, after_sequence, limit):
                self.calls.append((raw_table, after_sequence, limit))
                return list(self.responses.get((raw_table, after_sequence), []))

        raw_repository = SequencedRawRepository()
        cursor_repository = self.FakeProcessingCursorRepository()
        worker = self.FakeNormalizationWorker(cursor_repository)
        driver = NormalizationReplayDriver(
            raw_repository=raw_repository,
            processing_cursor_repository=cursor_repository,
            normalization_worker=worker,
        )

        result = driver.run_until_caught_up(
            raw_table='raw_operations',
            batch_limit=1,
            max_batches=3,
        )

        self.assertEqual(result['batch_count'], 2)
        self.assertTrue(result['caught_up'])

    def test_run_once_uses_explicit_after_sequence_without_loading_cursor(self):
        raw_repository = self.FakeRawRepository()
        raw_repository.items_by_table['raw_posted_messages'] = [
            {'raw_fact_id': '305', 'application_id': 'app-1', 'payload_kind': 'message'},
        ]
        cursor_repository = self.FakeProcessingCursorRepository({'last_sequence': '999'})
        driver = NormalizationReplayDriver(
            raw_repository=raw_repository,
            processing_cursor_repository=cursor_repository,
            normalization_worker=self.FakeNormalizationWorker(),
        )

        result = driver.run_once(
            raw_table='raw_posted_messages',
            after_sequence=301,
        )

        self.assertEqual(raw_repository.calls[0], ('raw_posted_messages', 301, 100))
        self.assertIsNone(result['cursor'])
        self.assertEqual(cursor_repository.calls, [])

    def test_run_all_until_caught_up_drains_all_configured_tables(self):
        class SequencedRawRepository(self.FakeRawRepository):
            def __init__(self):
                super().__init__()
                self.responses = {
                    ('raw_operations', None): [
                        {'raw_fact_id': '1', 'application_id': 'app-1', 'payload_kind': 'operation'},
                    ],
                    ('raw_operations', 1): [],
                    ('raw_posted_messages', None): [
                        {'raw_fact_id': '2', 'application_id': 'app-2', 'payload_kind': 'message'},
                    ],
                    ('raw_posted_messages', 2): [],
                    ('raw_events', None): [
                        {'raw_fact_id': '3', 'application_id': 'app-3', 'payload_kind': 'event'},
                    ],
                    ('raw_events', 3): [],
                }

            def list_normalization_candidates(self, *, raw_table, after_sequence, limit):
                self.calls.append((raw_table, after_sequence, limit))
                return list(self.responses.get((raw_table, after_sequence), []))

        class PartitionedCursorRepository:
            def __init__(self):
                self.loaded_cursors = {}
                self.calls = []

            def load_cursor(self, *, cursor_name, partition_key):
                self.calls.append((cursor_name, partition_key))
                return self.loaded_cursors.get(partition_key)

        class PartitionedWorker(self.FakeNormalizationWorker):
            def process_items(self, items, *, partition_key, reprocess_reason=None):
                self.calls.append((items, partition_key, reprocess_reason))
                if self.cursor_repository is not None:
                    self.cursor_repository.loaded_cursors[partition_key] = {
                        'last_sequence': items[-1]['raw_fact_id']
                    }
                return {
                    'processed_count': len(items),
                    'normalized_event_count': len(items),
                    'last_sequence': items[-1]['raw_fact_id'],
                    'last_block_hash': items[-1].get('target_block_hash'),
                }

        raw_repository = SequencedRawRepository()
        cursor_repository = PartitionedCursorRepository()
        worker = PartitionedWorker(cursor_repository)
        driver = NormalizationReplayDriver(
            raw_repository=raw_repository,
            processing_cursor_repository=cursor_repository,
            normalization_worker=worker,
            batch_limit=1,
        )

        result = driver.run_all_until_caught_up(reprocess_reason='post_ingest')

        self.assertEqual(result['table_count'], 3)
        self.assertEqual(result['processed_count'], 3)
        self.assertEqual(result['normalized_event_count'], 3)
        self.assertTrue(result['caught_up'])
