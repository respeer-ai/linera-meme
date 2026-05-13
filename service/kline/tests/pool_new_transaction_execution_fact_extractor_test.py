import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.pool_new_transaction_execution_fact_extractor import PoolNewTransactionExecutionFactExtractor  # noqa: E402


class PoolNewTransactionExecutionFactExtractorTest(unittest.TestCase):
    def test_extracts_execution_fact_from_pool_new_transaction_event(self):
        fact = PoolNewTransactionExecutionFactExtractor().extract(
            {
                'normalized_event_id': 'event-1',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'target_chain_id': 'pool-chain',
                'target_block_hash': 'block-1',
                'transaction_index': 9,
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction': {
                            'transaction_id': 21,
                            'transaction_type': 'BuyToken0',
                            'from': {'chain_id': 'user-chain', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'},
                            'amount_0_out': '77',
                            'amount_1_in': '8',
                            'created_at_micros': 777000,
                        },
                    },
                },
            }
        )

        self.assertEqual(fact.normalized_event_id, 'event-1')
        self.assertEqual(fact.application_id, 'pool-app')
        self.assertEqual(fact.pool_chain_id, 'pool-chain')
        self.assertEqual(fact.block_hash, 'block-1')
        self.assertEqual(fact.transaction_index, 9)
        self.assertEqual(fact.transaction_type(), 'BuyToken0')
        self.assertEqual(fact.transaction_id(), 21)
        self.assertEqual(fact.trade_time_ms(), 777)
        self.assertEqual(fact.from_account(), '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@user-chain')
        self.assertTrue(fact.is_trade())
        self.assertFalse(fact.is_liquidity_change())

    def test_falls_back_to_created_at_and_from_account_string(self):
        fact = PoolNewTransactionExecutionFactExtractor().extract(
            {
                'normalized_event_id': 'event-3',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'target_chain_id': 'pool-chain',
                'target_block_hash': 'block-3',
                'transaction_index': 3,
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction': {
                            'transaction_id': 22,
                            'transaction_type': 'SellToken0',
                            'from_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@user-chain',
                            'amount_0_in': '12',
                            'amount_1_out': '34',
                            'created_at': 888000,
                        },
                    },
                },
            }
        )

        self.assertEqual(fact.trade_time_ms(), 888000)
        self.assertEqual(fact.from_account(), '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@user-chain')
        self.assertEqual(fact.position_owner(), '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@user-chain')

    def test_falls_back_to_owner_string_when_from_fields_are_missing(self):
        fact = PoolNewTransactionExecutionFactExtractor().extract(
            {
                'normalized_event_id': 'event-4',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'target_chain_id': 'pool-chain',
                'target_block_hash': 'block-4',
                'transaction_index': 4,
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction': {
                            'transaction_id': 23,
                            'transaction_type': 'AddLiquidity',
                            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@user-chain',
                            'amount_0_in': '1',
                            'amount_1_in': '2',
                            'liquidity': '3',
                            'created_at_micros': 999000,
                        },
                    },
                },
            }
        )

        self.assertIsNone(fact.from_account())
        self.assertEqual(fact.position_owner(), '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@user-chain')

    def test_position_owner_is_none_when_owner_identity_is_missing(self):
        fact = PoolNewTransactionExecutionFactExtractor().extract(
            {
                'normalized_event_id': 'event-5',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'target_chain_id': 'pool-chain',
                'target_block_hash': 'block-5',
                'transaction_index': 5,
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction': {
                            'transaction_id': 24,
                            'transaction_type': 'AddLiquidity',
                            'amount_0_in': '1',
                            'amount_1_in': '2',
                            'liquidity': '3',
                            'created_at_micros': 1000,
                        },
                    },
                },
            }
        )

        self.assertIsNone(fact.from_account())
        self.assertIsNone(fact.position_owner())

    def test_returns_none_when_transaction_payload_is_missing(self):
        fact = PoolNewTransactionExecutionFactExtractor().extract(
            {
                'normalized_event_id': 'event-2',
                'application_id': 'pool-app',
                'event_payload_json': {'decoded_payload_json': {}},
            }
        )

        self.assertIsNone(fact)

    def test_raises_for_missing_required_event_keys(self):
        with self.assertRaises(ValueError) as context:
            PoolNewTransactionExecutionFactExtractor().extract(
                {
                    'application_id': 'pool-app',
                    'event_payload_json': {},
                }
            )

        self.assertIn('missing execution fact event keys', str(context.exception))
