import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from normalizer.decode_result_normalizer import DecodeResultNormalizer  # noqa: E402


class DecodeResultNormalizerTest(unittest.TestCase):
    def test_normalize_item_maps_unresolved_application_to_infra_event(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-1',
                'raw_table': 'raw_operations',
                'application_id': 'app-missing',
                'payload_kind': 'operation',
                'reprocess_reason': 'registry_updated',
                'decode_result': {
                    'status': 'unresolved_application',
                    'application_id': 'app-missing',
                    'payload_kind': 'operation',
                    'app_type': None,
                    'payload_type': None,
                    'decoded_payload_json': None,
                    'decode_error': 'application_id is not registered',
                    'metadata_json': None,
                    'decoder_version': None,
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'decode_unresolved')
        self.assertEqual(event['normalization_status'], 'decode_failed')
        self.assertEqual(event['event_type'], 'operation')
        self.assertEqual(event['reprocess_reason'], 'registry_updated')

    def test_normalize_item_builds_stable_correlation_key_for_decoded_payload(self):
        normalizer = DecodeResultNormalizer()
        item = {
            'raw_fact_id': 'raw-2',
            'raw_table': 'raw_operations',
            'application_id': 'app-ams',
            'payload_kind': 'operation',
            'chain_id': 'target-chain',
            'source_chain_id': 'source-chain',
            'source_cert_hash': 'cert-1',
            'transaction_index': 4,
            'decode_result': {
                'status': 'decoded',
                'application_id': 'app-ams',
                'payload_kind': 'operation',
                'app_type': 'ams',
                'payload_type': 'add_application_type',
                'decoded_payload_json': {'application_type': 'DeFi'},
                'decode_error': None,
                'metadata_json': {'source': 'seed'},
                'decoder_version': 'ams-op-v1',
            },
        }

        first = normalizer.normalize_item(item)
        second = normalizer.normalize_item(dict(item))

        first_event = first['normalized_events'][0]
        second_event = second['normalized_events'][0]
        self.assertEqual(first_event['event_family'], 'application_operation_observed')
        self.assertEqual(first_event['event_type'], 'add_application_type')
        self.assertEqual(first_event['normalization_status'], 'observed')
        self.assertEqual(first_event['correlation_key'], second_event['correlation_key'])
        self.assertEqual(
            first_event['correlation_key'],
            'ams:source-chain:cert-1:4:application_operation_observed',
        )

    def test_normalize_item_keeps_reject_visible_for_decoded_message(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-3',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-pool',
                'payload_kind': 'message',
                'chain_id': 'pool-chain',
                'source_chain_id': 'user-chain',
                'source_cert_hash': 'cert-2',
                'transaction_index': 9,
                'message_index': 1,
                'execution_status': 'rejected',
                'reject_reason': 'insufficient native balance for payout',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-pool',
                    'payload_kind': 'message',
                    'app_type': 'pool',
                    'payload_type': 'swap',
                    'decoded_payload_json': {'amount_0_in': '1'},
                    'decode_error': None,
                    'metadata_json': {'pool_id': '1002'},
                    'decoder_version': None,
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'pool_swap_message_rejected')
        self.assertEqual(event['normalization_status'], 'rejected')
        self.assertEqual(event['message_index'], 1)
        self.assertEqual(
            event['event_payload_json']['reject_reason'],
            'insufficient native balance for payout',
        )

    def test_normalize_item_rejects_invalid_contract_item(self):
        normalizer = DecodeResultNormalizer()

        with self.assertRaisesRegex(ValueError, 'missing normalize item keys'):
            normalizer.normalize_item(
                {
                    'raw_fact_id': 'raw-4',
                    'raw_table': 'raw_operations',
                }
            )

    def test_normalize_item_maps_pool_swap_operation_to_pool_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-5',
                'raw_table': 'raw_operations',
                'application_id': 'app-pool',
                'payload_kind': 'operation',
                'chain_id': 'pool-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-pool',
                    'payload_kind': 'operation',
                    'app_type': 'pool',
                    'payload_type': 'swap',
                    'decoded_payload_json': {'operation_type': 'swap'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'pool-operation-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'pool_swap_requested')
        self.assertEqual(event['event_type'], 'swap')

    def test_normalize_item_maps_pool_fund_success_message_to_pool_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-6',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-pool',
                'payload_kind': 'message',
                'chain_id': 'pool-chain',
                'source_chain_id': 'user-chain',
                'source_cert_hash': 'cert-6',
                'transaction_index': 6,
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-pool',
                    'payload_kind': 'message',
                    'app_type': 'pool',
                    'payload_type': 'fund_success',
                    'decoded_payload_json': {'message_type': 'fund_success'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'pool-message-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'pool_fund_success_recorded')

    def test_normalize_item_maps_rejected_pool_swap_message_to_pool_reject_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-7',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-pool',
                'payload_kind': 'message',
                'chain_id': 'pool-chain',
                'source_chain_id': 'user-chain',
                'source_cert_hash': 'cert-7',
                'transaction_index': 7,
                'message_index': 0,
                'execution_status': 'rejected',
                'reject_reason': 'incoming bundle action Reject',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-pool',
                    'payload_kind': 'message',
                    'app_type': 'pool',
                    'payload_type': 'swap',
                    'decoded_payload_json': {'message_type': 'swap'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'pool-message-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'pool_swap_message_rejected')

    def test_normalize_item_maps_swap_update_pool_operation_to_swap_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-8',
                'raw_table': 'raw_operations',
                'application_id': 'app-swap',
                'payload_kind': 'operation',
                'chain_id': 'swap-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-swap',
                    'payload_kind': 'operation',
                    'app_type': 'swap',
                    'payload_type': 'update_pool',
                    'decoded_payload_json': {'operation_type': 'update_pool'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'swap-operation-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'swap_update_pool_requested')
        self.assertEqual(event['event_type'], 'update_pool')

    def test_normalize_item_maps_rejected_swap_update_pool_message_to_swap_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-9',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-swap',
                'payload_kind': 'message',
                'chain_id': 'swap-chain',
                'source_chain_id': 'pool-chain',
                'source_cert_hash': 'cert-9',
                'transaction_index': 9,
                'execution_status': 'rejected',
                'reject_reason': 'incoming bundle action Reject',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-swap',
                    'payload_kind': 'message',
                    'app_type': 'swap',
                    'payload_type': 'update_pool',
                    'decoded_payload_json': {'message_type': 'update_pool'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'swap-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'swap_update_pool_message_rejected')
        self.assertEqual(event['normalization_status'], 'rejected')

    def test_normalize_item_maps_swap_pool_created_message_to_record_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-10',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-swap',
                'payload_kind': 'message',
                'chain_id': 'swap-chain',
                'source_chain_id': 'swap-root-chain',
                'source_cert_hash': 'cert-10',
                'transaction_index': 10,
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-swap',
                    'payload_kind': 'message',
                    'app_type': 'swap',
                    'payload_type': 'pool_created',
                    'decoded_payload_json': {'message_type': 'pool_created'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'swap-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'swap_pool_created_recorded')

    def test_normalize_item_maps_meme_transfer_operation_to_meme_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-11',
                'raw_table': 'raw_operations',
                'application_id': 'app-meme',
                'payload_kind': 'operation',
                'chain_id': 'meme-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-meme',
                    'payload_kind': 'operation',
                    'app_type': 'meme',
                    'payload_type': 'transfer',
                    'decoded_payload_json': {'operation_type': 'transfer'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'meme-operation-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'meme_transfer_requested')
        self.assertEqual(event['event_type'], 'transfer')

    def test_normalize_item_maps_rejected_meme_transfer_message_to_meme_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-12',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-meme',
                'payload_kind': 'message',
                'chain_id': 'meme-chain',
                'source_chain_id': 'wallet-chain',
                'source_cert_hash': 'cert-12',
                'transaction_index': 12,
                'reject_reason': 'application execution rejected',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-meme',
                    'payload_kind': 'message',
                    'app_type': 'meme',
                    'payload_type': 'transfer',
                    'decoded_payload_json': {'message_type': 'transfer'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'meme-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'meme_transfer_message_rejected')
        self.assertEqual(event['normalization_status'], 'rejected')

    def test_normalize_item_maps_meme_liquidity_funded_message_to_record_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-13',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-meme',
                'payload_kind': 'message',
                'chain_id': 'meme-chain',
                'source_chain_id': 'swap-chain',
                'source_cert_hash': 'cert-13',
                'transaction_index': 13,
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-meme',
                    'payload_kind': 'message',
                    'app_type': 'meme',
                    'payload_type': 'liquidity_funded',
                    'decoded_payload_json': {'message_type': 'liquidity_funded'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'meme-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'meme_liquidity_funded_recorded')
