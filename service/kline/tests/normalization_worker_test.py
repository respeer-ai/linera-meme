import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from normalizer.normalization_worker import NormalizationWorker  # noqa: E402


class NormalizationWorkerTest(unittest.TestCase):
    class FakeDecodeScheduler:
        def __init__(self, should_fail=False):
            self.should_fail = should_fail
            self.calls = []

        def decode_batch(self, items, *, reprocess_reason=None):
            self.calls.append((items, reprocess_reason))
            if self.should_fail:
                raise RuntimeError('decode failed')
            return [
                {
                    **item,
                    'reprocess_reason': reprocess_reason,
                    'decode_result': {
                        'status': 'decoded',
                        'application_id': item['application_id'],
                        'payload_kind': item['payload_kind'],
                        'app_type': 'ams',
                        'payload_type': 'add_application_type',
                        'decoded_payload_json': {'application_type': 'DeFi'},
                    },
                }
                for item in items
            ]

    class FakeNormalizedEventMaterializer:
        def __init__(self):
            self.calls = []

        def materialize_batch(self, decoded_batch):
            self.calls.append(decoded_batch)
            return [
                {
                    'raw_fact_id': item['raw_fact_id'],
                    'normalized_events': [
                        {'normalized_event_id': f"{item['raw_fact_id']}:event"}
                    ],
                }
                for item in decoded_batch
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

    def test_process_items_advances_cursor_after_decode_and_materialize(self):
        cursor_repo = self.FakeProcessingCursorRepository()
        worker = NormalizationWorker(
            decode_scheduler=self.FakeDecodeScheduler(),
            normalized_event_materializer=self.FakeNormalizedEventMaterializer(),
            processing_cursor_repository=cursor_repo,
        )

        result = worker.process_items(
            [
                {
                    'raw_fact_id': 'raw-1',
                    'application_id': 'app-1',
                    'payload_kind': 'operation',
                    'block_hash': 'block-1',
                },
                {
                    'raw_fact_id': 'raw-2',
                    'application_id': 'app-2',
                    'payload_kind': 'message',
                    'block_hash': 'block-2',
                },
            ],
            partition_key='chain-a',
            reprocess_reason='registry_updated',
        )

        self.assertEqual(result['processed_count'], 2)
        self.assertEqual(result['normalized_event_count'], 2)
        self.assertEqual(result['last_sequence'], 'raw-2')
        self.assertEqual(result['last_block_hash'], 'block-2')
        self.assertEqual(cursor_repo.attempts[0]['partition_key'], 'chain-a')
        self.assertEqual(cursor_repo.successes[0]['last_sequence'], 'raw-2')
        self.assertEqual(cursor_repo.failures, [])

    def test_process_items_marks_failure_when_decode_raises(self):
        cursor_repo = self.FakeProcessingCursorRepository()
        worker = NormalizationWorker(
            decode_scheduler=self.FakeDecodeScheduler(should_fail=True),
            normalized_event_materializer=self.FakeNormalizedEventMaterializer(),
            processing_cursor_repository=cursor_repo,
        )

        with self.assertRaisesRegex(RuntimeError, 'decode failed'):
            worker.process_items(
                [
                    {
                        'raw_fact_id': 'raw-1',
                        'application_id': 'app-1',
                        'payload_kind': 'operation',
                        'block_hash': 'block-1',
                    },
                ]
            )

        self.assertEqual(len(cursor_repo.attempts), 1)
        self.assertEqual(len(cursor_repo.failures), 1)
        self.assertEqual(cursor_repo.successes, [])

