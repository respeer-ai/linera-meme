import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.settled_market_deriver import SettledMarketDeriver  # noqa: E402


class SettledMarketDeriverTest(unittest.TestCase):
    def test_derives_settled_trade_from_pool_new_transaction_message(self):
        deriver = SettledMarketDeriver()

        derived = deriver.derive_item(
            {
                'normalized_event_id': 'event-1',
                'raw_fact_id': '11',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'normalization_status': 'observed',
                'target_chain_id': 'pool-chain',
                'target_block_hash': 'block-1',
                'transaction_index': 7,
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction': {
                            'transaction_id': 19,
                            'transaction_type': 'BuyToken0',
                            'from': {'chain_id': 'user-chain', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'},
                            'amount_0_in': None,
                            'amount_0_out': '300',
                            'amount_1_in': '25',
                            'amount_1_out': None,
                            'created_at_micros': 1234567000,
                        }
                    }
                },
            }
        )

        self.assertEqual(derived['derivation_status'], 'settled')
        trade = derived['settled_outputs'][0]
        self.assertEqual(trade['settled_output_type'], 'settled_trade')
        self.assertEqual(trade['pool_application_id'], 'pool-app')
        self.assertEqual(trade['pool_chain_id'], 'pool-chain')
        self.assertEqual(trade['from_account'], '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@user-chain')
        self.assertEqual(trade['amount_0_out'], '300')
        self.assertEqual(trade['amount_1_in'], '25')
        self.assertEqual(trade['trade_time_ms'], 1234567)
        self.assertEqual(trade['side'], 'buy_token_0')
        self.assertEqual(trade['amount_in'], '25')
        self.assertEqual(trade['amount_out'], '300')

    def test_derives_add_liquidity_change_from_new_transaction_message(self):
        deriver = SettledMarketDeriver()

        derived = deriver.derive_item(
            {
                'normalized_event_id': 'event-2',
                'raw_fact_id': '12',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'normalization_status': 'observed',
                'target_chain_id': 'pool-chain',
                'target_block_hash': 'block-2',
                'transaction_index': 8,
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction': {
                            'transaction_id': 20,
                            'transaction_type': 'AddLiquidity',
                            'from': {'chain_id': 'user-chain', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'},
                            'amount_0_in': '1000',
                            'amount_1_in': '55',
                            'liquidity': '888',
                            'created_at_micros': 555000,
                        }
                    }
                },
            }
        )

        self.assertEqual(derived['derivation_status'], 'settled')
        change = derived['settled_outputs'][0]
        self.assertEqual(change['settled_output_type'], 'settled_liquidity_change')
        self.assertEqual(change['change_type'], 'add_liquidity')
        self.assertEqual(change['owner'], '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@user-chain')
        self.assertEqual(change['liquidity_delta'], '888')
        self.assertTrue(change['is_position_liquidity'])
        self.assertEqual(change['liquidity_semantics'], 'position_liquidity')
        self.assertEqual(change['amount_0_delta'], '1000')
        self.assertEqual(change['amount_1_delta'], '55')
        self.assertEqual(change['event_time_ms'], 555)

    def test_derives_zero_liquidity_add_as_virtual_initial_liquidity_not_position_liquidity(self):
        deriver = SettledMarketDeriver()

        derived = deriver.derive_item(
            {
                'normalized_event_id': 'event-2-virtual',
                'raw_fact_id': '12',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'normalization_status': 'observed',
                'target_chain_id': 'pool-chain',
                'target_block_hash': 'block-2',
                'transaction_index': 8,
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction': {
                            'transaction_id': 20,
                            'transaction_type': 'AddLiquidity',
                            'from': {'chain_id': 'user-chain', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'},
                            'amount_0_in': '1000',
                            'amount_1_in': '55',
                            'liquidity': '0',
                            'created_at_micros': 555000,
                        }
                    }
                },
            }
        )

        self.assertEqual(derived['derivation_status'], 'settled')
        change = derived['settled_outputs'][0]
        self.assertEqual(change['settled_output_type'], 'settled_liquidity_change')
        self.assertEqual(change['change_type'], 'add_liquidity')
        self.assertEqual(change['liquidity_delta'], '0')
        self.assertFalse(change['is_position_liquidity'])
        self.assertEqual(change['liquidity_semantics'], 'virtual_initial_liquidity')

    def test_derives_remove_liquidity_change_from_new_transaction_message(self):
        deriver = SettledMarketDeriver()

        derived = deriver.derive_item(
            {
                'normalized_event_id': 'event-3',
                'raw_fact_id': '13',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'normalization_status': 'observed',
                'target_chain_id': 'pool-chain',
                'target_block_hash': 'block-3',
                'transaction_index': 9,
                'event_payload_json': {
                    'decoded_payload_json': {
                        'transaction': {
                            'transaction_id': 21,
                            'transaction_type': 'RemoveLiquidity',
                            'from': {'chain_id': 'user-chain', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'},
                            'amount_0_out': '77',
                            'amount_1_out': '8',
                            'liquidity': '9',
                            'created_at_micros': 777000,
                        }
                    }
                },
            }
        )

        self.assertEqual(derived['derivation_status'], 'settled')
        change = derived['settled_outputs'][0]
        self.assertEqual(change['change_type'], 'remove_liquidity')
        self.assertEqual(change['liquidity_delta'], '9')
        self.assertEqual(change['amount_0_delta'], '77')
        self.assertEqual(change['amount_1_delta'], '8')
        self.assertEqual(change['event_time_ms'], 777)

    def test_blocks_when_new_transaction_payload_is_missing(self):
        deriver = SettledMarketDeriver()

        derived = deriver.derive_item(
            {
                'normalized_event_id': 'event-4',
                'raw_fact_id': '14',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'normalization_status': 'observed',
                'event_payload_json': {'decoded_payload_json': {}},
            }
        )

        self.assertEqual(derived['derivation_status'], 'blocked_missing_context')
        self.assertEqual(derived['settled_outputs'], [])

    def test_ignores_non_observed_or_non_executed_events(self):
        deriver = SettledMarketDeriver()

        rejected = deriver.derive_item(
            {
                'normalized_event_id': 'event-5',
                'raw_fact_id': '15',
                'application_id': 'pool-app',
                'event_family': 'pool_new_transaction_recorded',
                'normalization_status': 'rejected',
                'event_payload_json': {},
            }
        )
        other_family = deriver.derive_item(
            {
                'normalized_event_id': 'event-6',
                'raw_fact_id': '16',
                'application_id': 'pool-app',
                'event_family': 'pool_swap_message_observed',
                'normalization_status': 'observed',
                'event_payload_json': {},
            }
        )

        self.assertEqual(rejected['derivation_status'], 'ignored_non_settled')
        self.assertEqual(other_family['derivation_status'], 'ignored_non_settled')


if __name__ == '__main__':
    unittest.main()
