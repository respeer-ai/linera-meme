import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from normalizer.decode_result_normalizer import DecodeResultNormalizer  # noqa: E402
from normalizer.normalized_event_materializer import NormalizedEventMaterializer  # noqa: E402


class NormalizedEventMaterializerTest(unittest.TestCase):
    class FakeNormalizedEventRepository:
        def __init__(self):
            self.events = []

        def upsert_normalized_events(self, events):
            self.events.extend(events)
            return len(events)

    class FakePoolCatalogProjectionMaterializer:
        def __init__(self):
            self.events = []

        def materialize_events(self, events):
            self.events.extend(events)
            return {'materialized_count': len(events)}

    class FakePoolFeeToHistoryProjectionMaterializer:
        def __init__(self):
            self.events = []

        def materialize_events(self, events):
            self.events.extend(events)
            return {'materialized_count': len(events)}

    def test_materialize_item_normalizes_and_persists_events(self):
        repository = self.FakeNormalizedEventRepository()
        materializer = NormalizedEventMaterializer(
            decode_result_normalizer=DecodeResultNormalizer(),
            normalized_event_repository=repository,
        )

        normalized = materializer.materialize_item(
            {
                'raw_fact_id': 'raw-1',
                'raw_table': 'raw_operations',
                'application_id': 'app-ams',
                'payload_kind': 'operation',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-ams',
                    'payload_kind': 'operation',
                    'app_type': 'ams',
                    'payload_type': 'add_application_type',
                    'decoded_payload_json': {'application_type': 'DeFi'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'ams-op-v1',
                },
            }
        )

        self.assertEqual(len(normalized['normalized_events']), 1)
        self.assertEqual(len(repository.events), 1)
        self.assertEqual(
            repository.events[0]['event_family'],
            'ams_add_application_type_requested',
        )

    def test_materialize_batch_flattens_and_persists_all_events(self):
        repository = self.FakeNormalizedEventRepository()
        materializer = NormalizedEventMaterializer(
            decode_result_normalizer=DecodeResultNormalizer(),
            normalized_event_repository=repository,
        )

        materializer.materialize_batch(
            [
                {
                    'raw_fact_id': 'raw-1',
                    'raw_table': 'raw_operations',
                    'application_id': 'app-a',
                    'payload_kind': 'operation',
                    'decode_result': {
                        'status': 'unresolved_application',
                        'application_id': 'app-a',
                        'payload_kind': 'operation',
                    },
                },
                {
                    'raw_fact_id': 'raw-2',
                    'raw_table': 'raw_posted_messages',
                    'application_id': 'app-b',
                    'payload_kind': 'message',
                    'execution_status': 'rejected',
                    'decode_result': {
                        'status': 'decoded',
                        'application_id': 'app-b',
                        'payload_kind': 'message',
                        'app_type': 'pool',
                        'payload_type': 'swap',
                        'decoded_payload_json': {'amount_0_in': '1'},
                    },
                },
            ]
        )

        self.assertEqual(len(repository.events), 2)
        self.assertEqual(repository.events[0]['event_family'], 'decode_unresolved')
        self.assertEqual(repository.events[1]['event_family'], 'pool_swap_message_rejected')

    def test_materialize_batch_forwards_normalized_events_to_pool_fee_to_history_projection(self):
        repository = self.FakeNormalizedEventRepository()
        pool_fee_to_history_materializer = self.FakePoolFeeToHistoryProjectionMaterializer()
        materializer = NormalizedEventMaterializer(
            decode_result_normalizer=DecodeResultNormalizer(),
            normalized_event_repository=repository,
            pool_fee_to_history_projection_materializer=pool_fee_to_history_materializer,
        )

        materializer.materialize_batch([
            {
                'raw_fact_id': 'raw-1',
                'raw_table': 'raw_posted_messages',
                'application_id': 'swap-app',
                'payload_kind': 'message',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'swap-app',
                    'payload_kind': 'message',
                    'app_type': 'swap',
                    'payload_type': 'pool_created',
                    'decoded_payload_json': {
                        'message_type': 'pool_created',
                        'pool_application': {'chain_id': 'chain-a', 'owner': 'pool-app'},
                        'token_0': 'AAA',
                        'token_1': None,
                    },
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'swap-message-rust-v1',
                },
            }
        ])

        self.assertEqual(len(pool_fee_to_history_materializer.events), 1)
        self.assertEqual(
            pool_fee_to_history_materializer.events[0]['event_family'],
            'swap_pool_created_recorded',
        )

    def test_materialize_batch_forwards_normalized_events_to_pool_catalog_projection(self):
        repository = self.FakeNormalizedEventRepository()
        pool_catalog_materializer = self.FakePoolCatalogProjectionMaterializer()
        materializer = NormalizedEventMaterializer(
            decode_result_normalizer=DecodeResultNormalizer(),
            normalized_event_repository=repository,
            pool_catalog_projection_materializer=pool_catalog_materializer,
        )

        materializer.materialize_batch([
            {
                'raw_fact_id': 'raw-1',
                'raw_table': 'raw_posted_messages',
                'application_id': 'swap-app',
                'payload_kind': 'message',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'swap-app',
                    'payload_kind': 'message',
                    'app_type': 'swap',
                    'payload_type': 'pool_created',
                    'decoded_payload_json': {
                        'message_type': 'pool_created',
                        'pool_application': {'chain_id': 'chain-a', 'owner': 'pool-app'},
                        'token_0': 'AAA',
                        'token_1': None,
                    },
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'swap-message-rust-v1',
                },
            }
        ])

        self.assertEqual(len(pool_catalog_materializer.events), 1)
        self.assertEqual(
            pool_catalog_materializer.events[0]['event_family'],
            'swap_pool_created_recorded',
        )
