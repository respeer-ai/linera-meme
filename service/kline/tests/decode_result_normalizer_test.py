import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from normalizer.decode_result_normalizer import DecodeResultNormalizer  # noqa: E402


class DecodeResultNormalizerTest(unittest.TestCase):
    def build_decoded_payload_json(self, payload_kind: str, payload_type: str) -> dict:
        if payload_kind == 'event' and payload_type == 'swap_executed':
            return {
                'execution': {
                    'transaction_id': 1,
                    'executed_at_micros': 123456,
                    'from': {'chain_id': 'pool-chain', 'owner': '0xpool'},
                    'trade_type': 'buy_token_0',
                    'amount_0_out': '10',
                    'amount_1_in': '2',
                }
            }
        if payload_kind == 'event' and payload_type == 'add_liquidity_executed':
            return {
                'execution': {
                    'transaction_id': 1,
                    'executed_at_micros': 123456,
                    'from': {'chain_id': 'pool-chain', 'owner': '0xpool'},
                    'change_type': 'add_liquidity',
                    'amount_0_in': '10',
                    'amount_1_in': '2',
                    'liquidity': '20',
                }
            }
        if payload_kind == 'event' and payload_type == 'remove_liquidity_executed':
            return {
                'execution': {
                    'transaction_id': 1,
                    'executed_at_micros': 123456,
                    'from': {'chain_id': 'pool-chain', 'owner': '0xpool'},
                    'change_type': 'remove_liquidity',
                    'amount_0_out': '10',
                    'amount_1_out': '2',
                    'liquidity': '20',
                }
            }
        return {'payload_type': payload_type}

    def assert_normalized_family(
        self,
        *,
        app_type: str,
        payload_kind: str,
        payload_type: str,
        expected_family: str,
        expected_status: str = 'observed',
        rejected: bool = False,
    ) -> None:
        normalizer = DecodeResultNormalizer()
        item = {
            'raw_fact_id': f'raw-{app_type}-{payload_kind}-{payload_type}',
            'raw_table': {
                'operation': 'raw_operations',
                'message': 'raw_posted_messages',
                'event': 'raw_events',
            }[payload_kind],
            'application_id': f'app-{app_type}',
            'payload_kind': payload_kind,
            'chain_id': f'{app_type}-chain',
            'source_chain_id': f'{app_type}-source-chain',
            'source_cert_hash': f'cert-{app_type}-{payload_type}',
            'transaction_index': 1,
            'decode_result': {
                'status': 'decoded',
                'application_id': f'app-{app_type}',
                'payload_kind': payload_kind,
                'app_type': app_type,
                'payload_type': payload_type,
                'decoded_payload_json': self.build_decoded_payload_json(payload_kind, payload_type),
                'decode_error': None,
                'metadata_json': None,
                'decoder_version': f'{app_type}-{payload_kind}-rust-v1',
            },
        }
        if payload_kind == 'message':
            item['message_index'] = 0
        if rejected:
            item['execution_status'] = 'rejected'
            item['reject_reason'] = 'incoming bundle action Reject'

        normalized = normalizer.normalize_item(item)

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], expected_family)
        self.assertEqual(event['event_type'], payload_type)
        self.assertEqual(event['normalization_status'], expected_status)

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
        self.assertEqual(first_event['event_family'], 'ams_add_application_type_requested')
        self.assertEqual(first_event['event_type'], 'add_application_type')
        self.assertEqual(first_event['normalization_status'], 'observed')
        self.assertEqual(first_event['correlation_key'], second_event['correlation_key'])
        self.assertEqual(
            first_event['correlation_key'],
            'ams:source-chain:cert-1:4:ams_add_application_type_requested',
        )

    def test_normalize_item_maps_ams_add_application_type_operation_to_specific_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-2b',
                'raw_table': 'raw_operations',
                'application_id': 'app-ams',
                'payload_kind': 'operation',
                'chain_id': 'target-chain',
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

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'ams_add_application_type_requested')
        self.assertEqual(event['event_type'], 'add_application_type')

    def test_normalize_item_maps_ams_add_application_type_message_to_specific_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-2c',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-ams',
                'payload_kind': 'message',
                'chain_id': 'target-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-ams',
                    'payload_kind': 'message',
                    'app_type': 'ams',
                    'payload_type': 'add_application_type',
                    'decoded_payload_json': {'application_type': 'DeFi'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'ams-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'ams_add_application_type_recorded')
        self.assertEqual(event['event_type'], 'add_application_type')

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

    def test_normalize_item_maps_pool_new_transaction_message_to_execution_fact_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-6b',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-pool',
                'payload_kind': 'message',
                'chain_id': 'pool-chain',
                'source_chain_id': 'pool-chain',
                'source_cert_hash': 'cert-6b',
                'transaction_index': 6,
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-pool',
                    'payload_kind': 'message',
                    'app_type': 'pool',
                    'payload_type': 'new_transaction',
                    'decoded_payload_json': {
                        'message_type': 'new_transaction',
                        'transaction': {'transaction_id': 1},
                    },
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'pool-message-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'pool_new_transaction_recorded')
        self.assertEqual(event['event_type'], 'new_transaction')

    def test_normalize_item_maps_unimplemented_pool_event_to_decode_unimplemented(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-pool-event-1',
                'raw_table': 'raw_events',
                'application_id': 'app-pool',
                'payload_kind': 'event',
                'chain_id': 'pool-chain',
                'transaction_index': 17,
                'decode_result': {
                    'status': 'unimplemented_decoder',
                    'application_id': 'app-pool',
                    'payload_kind': 'event',
                    'app_type': 'pool',
                    'payload_type': None,
                    'decoded_payload_json': None,
                    'decode_error': 'pool:event canonical decoding is not implemented',
                    'metadata_json': None,
                    'decoder_version': 'pool-event-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'decode_unimplemented')
        self.assertEqual(event['normalization_status'], 'decode_failed')
        self.assertEqual(event['event_type'], 'event')

    def test_normalize_item_maps_pool_executed_event_to_executed_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-pool-event-2',
                'raw_table': 'raw_events',
                'application_id': 'app-pool',
                'payload_kind': 'event',
                'chain_id': 'pool-chain',
                'transaction_index': 18,
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-pool',
                    'payload_kind': 'event',
                    'app_type': 'pool',
                    'payload_type': 'swap_executed',
                    'decoded_payload_json': {
                        'execution': {
                            'transaction_id': 18,
                            'executed_at_micros': 123456,
                            'from': {'chain_id': 'pool-chain', 'owner': '0xpool'},
                            'trade_type': 'buy_token_0',
                            'amount_0_out': '10',
                            'amount_1_in': '2',
                        }
                    },
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'pool-event-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'pool_swap_executed')
        self.assertEqual(event['event_type'], 'swap_executed')
        self.assertEqual(event['normalization_status'], 'observed')

    def test_normalize_item_downgrades_invalid_pool_executed_shape_to_decode_failed(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-6c',
                'raw_table': 'raw_events',
                'application_id': 'app-pool',
                'payload_kind': 'event',
                'chain_id': 'pool-chain',
                'transaction_index': 19,
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-pool',
                    'payload_kind': 'event',
                    'app_type': 'pool',
                    'payload_type': 'swap_executed',
                    'decoded_payload_json': {
                        'execution': {
                            'transaction_id': 19,
                            'executed_at_micros': 123457,
                            'from': {'chain_id': 'pool-chain', 'owner': '0xpool'},
                            'trade_type': 'buy_token_0',
                            'amount_1_in': '2',
                        }
                    },
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'pool-event-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'decode_failed')
        self.assertEqual(event['event_type'], 'event')
        self.assertEqual(event['normalization_status'], 'decode_failed')
        self.assertIn(
            'amount_0_out',
            event['event_payload_json']['decode_error'],
        )

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

    def test_normalize_item_maps_meme_creator_chain_id_operation_to_meme_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-13b',
                'raw_table': 'raw_operations',
                'application_id': 'app-meme',
                'payload_kind': 'operation',
                'chain_id': 'meme-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-meme',
                    'payload_kind': 'operation',
                    'app_type': 'meme',
                    'payload_type': 'creator_chain_id',
                    'decoded_payload_json': {'operation_type': 'creator_chain_id'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'meme-operation-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'meme_creator_chain_id_requested')
        self.assertEqual(event['event_type'], 'creator_chain_id')

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

    def test_normalize_item_maps_meme_transfer_from_operation_to_specific_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-14',
                'raw_table': 'raw_operations',
                'application_id': 'app-meme',
                'payload_kind': 'operation',
                'chain_id': 'meme-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-meme',
                    'payload_kind': 'operation',
                    'app_type': 'meme',
                    'payload_type': 'transfer_from',
                    'decoded_payload_json': {'operation_type': 'transfer_from'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'meme-operation-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'meme_transfer_from_requested')
        self.assertEqual(event['event_type'], 'transfer_from')

    def test_normalize_item_maps_observed_meme_mint_message_to_specific_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-15',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-meme',
                'payload_kind': 'message',
                'chain_id': 'meme-chain',
                'source_chain_id': 'wallet-chain',
                'source_cert_hash': 'cert-15',
                'transaction_index': 15,
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-meme',
                    'payload_kind': 'message',
                    'app_type': 'meme',
                    'payload_type': 'mint',
                    'decoded_payload_json': {'message_type': 'mint'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'meme-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'meme_mint_message_observed')
        self.assertEqual(event['normalization_status'], 'observed')

    def test_normalize_item_maps_proxy_register_miner_operation_to_proxy_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-16',
                'raw_table': 'raw_operations',
                'application_id': 'app-proxy',
                'payload_kind': 'operation',
                'chain_id': 'proxy-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-proxy',
                    'payload_kind': 'operation',
                    'app_type': 'proxy',
                    'payload_type': 'register_miner',
                    'decoded_payload_json': {'operation_type': 'register_miner'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'proxy-operation-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'proxy_register_miner_requested')
        self.assertEqual(event['event_type'], 'register_miner')

    def test_normalize_item_maps_proxy_deregister_miner_operation_to_proxy_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-17',
                'raw_table': 'raw_operations',
                'application_id': 'app-proxy',
                'payload_kind': 'operation',
                'chain_id': 'proxy-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-proxy',
                    'payload_kind': 'operation',
                    'app_type': 'proxy',
                    'payload_type': 'deregister_miner',
                    'decoded_payload_json': {'operation_type': 'deregister_miner'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'proxy-operation-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'proxy_deregister_miner_requested')
        self.assertEqual(event['event_type'], 'deregister_miner')

    def test_normalize_item_maps_proxy_register_miner_message_to_proxy_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-18',
                'raw_table': 'raw_messages',
                'application_id': 'app-proxy',
                'payload_kind': 'message',
                'chain_id': 'proxy-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-proxy',
                    'payload_kind': 'message',
                    'app_type': 'proxy',
                    'payload_type': 'register_miner',
                    'decoded_payload_json': {'message_type': 'register_miner'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'proxy-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'proxy_register_miner_message_observed')
        self.assertEqual(event['event_type'], 'register_miner')

    def test_normalize_item_maps_rejected_proxy_register_miner_message_to_proxy_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-19',
                'raw_table': 'raw_messages',
                'application_id': 'app-proxy',
                'payload_kind': 'message',
                'chain_id': 'proxy-chain',
                'reject_reason': 'budget_exhausted',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-proxy',
                    'payload_kind': 'message',
                    'app_type': 'proxy',
                    'payload_type': 'register_miner',
                    'decoded_payload_json': {'message_type': 'register_miner'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'proxy-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'proxy_register_miner_message_rejected')
        self.assertEqual(event['normalization_status'], 'rejected')

    def test_normalize_item_maps_proxy_meme_created_message_to_recorded_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-20',
                'raw_table': 'raw_messages',
                'application_id': 'app-proxy',
                'payload_kind': 'message',
                'chain_id': 'proxy-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-proxy',
                    'payload_kind': 'message',
                    'app_type': 'proxy',
                    'payload_type': 'meme_created',
                    'decoded_payload_json': {'message_type': 'meme_created'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'proxy-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'proxy_meme_created_recorded')
        self.assertEqual(event['event_type'], 'meme_created')

    def test_normalize_item_maps_blob_gateway_register_operation_to_specific_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-21',
                'raw_table': 'raw_operations',
                'application_id': 'app-blob',
                'payload_kind': 'operation',
                'chain_id': 'blob-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-blob',
                    'payload_kind': 'operation',
                    'app_type': 'blob-gateway',
                    'payload_type': 'blob_gateway_register',
                    'decoded_payload_json': {'operation_type': 'register'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'blob-gateway-operation-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'blob_gateway_register_requested')
        self.assertEqual(event['event_type'], 'blob_gateway_register')

    def test_normalize_item_maps_blob_gateway_register_message_to_specific_family(self):
        normalizer = DecodeResultNormalizer()

        normalized = normalizer.normalize_item(
            {
                'raw_fact_id': 'raw-22',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-blob',
                'payload_kind': 'message',
                'chain_id': 'blob-chain',
                'decode_result': {
                    'status': 'decoded',
                    'application_id': 'app-blob',
                    'payload_kind': 'message',
                    'app_type': 'blob-gateway',
                    'payload_type': 'blob_gateway_register',
                    'decoded_payload_json': {'message_type': 'register'},
                    'decode_error': None,
                    'metadata_json': None,
                    'decoder_version': 'blob-gateway-message-rust-v1',
                },
            }
        )

        event = normalized['normalized_events'][0]
        self.assertEqual(event['event_family'], 'blob_gateway_register_recorded')
        self.assertEqual(event['event_type'], 'blob_gateway_register')

    def test_normalize_item_covers_remaining_pool_family_mappings(self):
        cases = [
            ('operation', 'set_fee_to_setter', 'pool_set_fee_to_setter_requested', 'observed', False),
            ('message', 'request_fund', 'pool_fund_request_recorded', 'observed', False),
            ('message', 'fund_fail', 'pool_fund_fail_recorded', 'observed', False),
            ('message', 'add_liquidity', 'pool_add_liquidity_message_observed', 'observed', False),
            ('message', 'remove_liquidity', 'pool_remove_liquidity_message_observed', 'observed', False),
            ('message', 'set_fee_to', 'pool_set_fee_to_message_observed', 'observed', False),
            ('message', 'set_fee_to_setter', 'pool_set_fee_to_setter_message_observed', 'observed', False),
            ('message', 'add_liquidity', 'pool_add_liquidity_message_rejected', 'rejected', True),
            ('message', 'remove_liquidity', 'pool_remove_liquidity_message_rejected', 'rejected', True),
            ('message', 'set_fee_to', 'pool_set_fee_to_message_rejected', 'rejected', True),
            ('message', 'set_fee_to_setter', 'pool_set_fee_to_setter_message_rejected', 'rejected', True),
            ('event', 'add_liquidity_executed', 'pool_add_liquidity_executed', 'observed', False),
            ('event', 'remove_liquidity_executed', 'pool_remove_liquidity_executed', 'observed', False),
        ]
        for payload_kind, payload_type, expected_family, expected_status, rejected in cases:
            with self.subTest(payload_kind=payload_kind, payload_type=payload_type):
                self.assert_normalized_family(
                    app_type='pool',
                    payload_kind=payload_kind,
                    payload_type=payload_type,
                    expected_family=expected_family,
                    expected_status=expected_status,
                    rejected=rejected,
                )

    def test_normalize_item_covers_remaining_swap_family_mappings(self):
        cases = [
            ('operation', 'initialize_liquidity', 'swap_initialize_liquidity_requested', 'observed', False),
            ('operation', 'create_pool', 'swap_create_pool_requested', 'observed', False),
            ('message', 'create_user_pool', 'swap_create_user_pool_recorded', 'observed', False),
            ('message', 'user_pool_created', 'swap_user_pool_created_recorded', 'observed', False),
            ('message', 'initialize_liquidity', 'swap_initialize_liquidity_message_observed', 'observed', False),
            ('message', 'create_pool', 'swap_create_pool_message_observed', 'observed', False),
            ('message', 'initialize_liquidity', 'swap_initialize_liquidity_message_rejected', 'rejected', True),
            ('message', 'create_pool', 'swap_create_pool_message_rejected', 'rejected', True),
        ]
        for payload_kind, payload_type, expected_family, expected_status, rejected in cases:
            with self.subTest(payload_kind=payload_kind, payload_type=payload_type):
                self.assert_normalized_family(
                    app_type='swap',
                    payload_kind=payload_kind,
                    payload_type=payload_type,
                    expected_family=expected_family,
                    expected_status=expected_status,
                    rejected=rejected,
                )

    def test_normalize_item_covers_remaining_meme_family_mappings(self):
        cases = [
            ('operation', 'transfer_from_application', 'meme_transfer_from_application_requested', 'observed', False),
            ('operation', 'initialize_liquidity', 'meme_initialize_liquidity_requested', 'observed', False),
            ('operation', 'approve', 'meme_approve_requested', 'observed', False),
            ('operation', 'transfer_ownership', 'meme_transfer_ownership_requested', 'observed', False),
            ('operation', 'mine', 'meme_mine_requested', 'observed', False),
            ('operation', 'transfer_to_caller', 'meme_transfer_to_caller_requested', 'observed', False),
            ('operation', 'mint', 'meme_mint_requested', 'observed', False),
            ('operation', 'redeem', 'meme_redeem_requested', 'observed', False),
            ('message', 'transfer_from', 'meme_transfer_from_message_observed', 'observed', False),
            ('message', 'transfer_from_application', 'meme_transfer_from_application_message_observed', 'observed', False),
            ('message', 'initialize_liquidity', 'meme_initialize_liquidity_message_observed', 'observed', False),
            ('message', 'approve', 'meme_approve_message_observed', 'observed', False),
            ('message', 'transfer_ownership', 'meme_transfer_ownership_message_observed', 'observed', False),
            ('message', 'redeem', 'meme_redeem_message_observed', 'observed', False),
            ('message', 'transfer_from', 'meme_transfer_from_message_rejected', 'rejected', True),
            ('message', 'transfer_from_application', 'meme_transfer_from_application_message_rejected', 'rejected', True),
            ('message', 'initialize_liquidity', 'meme_initialize_liquidity_message_rejected', 'rejected', True),
            ('message', 'approve', 'meme_approve_message_rejected', 'rejected', True),
            ('message', 'transfer_ownership', 'meme_transfer_ownership_message_rejected', 'rejected', True),
            ('message', 'mint', 'meme_mint_message_rejected', 'rejected', True),
            ('message', 'redeem', 'meme_redeem_message_rejected', 'rejected', True),
        ]
        for payload_kind, payload_type, expected_family, expected_status, rejected in cases:
            with self.subTest(payload_kind=payload_kind, payload_type=payload_type):
                self.assert_normalized_family(
                    app_type='meme',
                    payload_kind=payload_kind,
                    payload_type=payload_type,
                    expected_family=expected_family,
                    expected_status=expected_status,
                    rejected=rejected,
                )

    def test_normalize_item_covers_remaining_proxy_family_mappings(self):
        cases = [
            ('operation', 'propose_add_genesis_miner', 'proxy_propose_add_genesis_miner_requested', 'observed', False),
            ('operation', 'approve_add_genesis_miner', 'proxy_approve_add_genesis_miner_requested', 'observed', False),
            ('operation', 'propose_remove_genesis_miner', 'proxy_propose_remove_genesis_miner_requested', 'observed', False),
            ('operation', 'approve_remove_genesis_miner', 'proxy_approve_remove_genesis_miner_requested', 'observed', False),
            ('operation', 'create_meme', 'proxy_create_meme_requested', 'observed', False),
            ('operation', 'propose_add_operator', 'proxy_propose_add_operator_requested', 'observed', False),
            ('operation', 'approve_add_operator', 'proxy_approve_add_operator_requested', 'observed', False),
            ('operation', 'propose_ban_operator', 'proxy_propose_ban_operator_requested', 'observed', False),
            ('operation', 'approve_ban_operator', 'proxy_approve_ban_operator_requested', 'observed', False),
            ('message', 'propose_add_genesis_miner', 'proxy_propose_add_genesis_miner_message_observed', 'observed', False),
            ('message', 'approve_add_genesis_miner', 'proxy_approve_add_genesis_miner_message_observed', 'observed', False),
            ('message', 'propose_remove_genesis_miner', 'proxy_propose_remove_genesis_miner_message_observed', 'observed', False),
            ('message', 'approve_remove_genesis_miner', 'proxy_approve_remove_genesis_miner_message_observed', 'observed', False),
            ('message', 'deregister_miner', 'proxy_deregister_miner_message_observed', 'observed', False),
            ('message', 'create_meme', 'proxy_create_meme_message_observed', 'observed', False),
            ('message', 'create_meme_ext', 'proxy_create_meme_ext_message_observed', 'observed', False),
            ('message', 'propose_add_operator', 'proxy_propose_add_operator_message_observed', 'observed', False),
            ('message', 'approve_add_operator', 'proxy_approve_add_operator_message_observed', 'observed', False),
            ('message', 'propose_ban_operator', 'proxy_propose_ban_operator_message_observed', 'observed', False),
            ('message', 'approve_ban_operator', 'proxy_approve_ban_operator_message_observed', 'observed', False),
            ('message', 'create_meme_ext', 'proxy_create_meme_ext_message_rejected', 'rejected', True),
            ('message', 'approve_ban_operator', 'proxy_approve_ban_operator_message_rejected', 'rejected', True),
        ]
        for payload_kind, payload_type, expected_family, expected_status, rejected in cases:
            with self.subTest(payload_kind=payload_kind, payload_type=payload_type):
                self.assert_normalized_family(
                    app_type='proxy',
                    payload_kind=payload_kind,
                    payload_type=payload_type,
                    expected_family=expected_family,
                    expected_status=expected_status,
                    rejected=rejected,
                )

    def test_normalize_item_covers_remaining_ams_family_mappings(self):
        cases = [
            ('operation', 'register', 'ams_register_requested'),
            ('operation', 'claim', 'ams_claim_requested'),
            ('operation', 'update', 'ams_update_requested'),
            ('message', 'register', 'ams_register_recorded'),
            ('message', 'claim', 'ams_claim_recorded'),
            ('message', 'update', 'ams_update_recorded'),
        ]
        for payload_kind, payload_type, expected_family in cases:
            with self.subTest(payload_kind=payload_kind, payload_type=payload_type):
                self.assert_normalized_family(
                    app_type='ams',
                    payload_kind=payload_kind,
                    payload_type=payload_type,
                    expected_family=expected_family,
                )
