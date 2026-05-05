import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.settled_product_transaction_adapter import SettledProductTransactionAdapter  # noqa: E402


class SettledProductTransactionAdapterTest(unittest.TestCase):
    def test_build_trade_history_row_uses_explicit_projection_fields(self):
        adapter = SettledProductTransactionAdapter()

        row = adapter.build_trade_history_row(
            {
                'transaction_id': 11,
                'side': 'buy_token_0',
                'amount_0_in': '0',
                'amount_0_out': '9',
                'amount_1_in': '10',
                'amount_1_out': '0',
                'trade_time_ms': 1234,
                'from_account': 'chain-a:owner-a',
            }
        )

        self.assertEqual(
            row,
            {
                'transaction_id': 11,
                'transaction_type': 'BuyToken0',
                'amount_0_in': '0',
                'amount_0_out': '9',
                'amount_1_in': '10',
                'amount_1_out': '0',
                'liquidity': None,
                'created_at': 1234,
                'from_account': 'chain-a:owner-a',
            },
        )

    def test_build_trade_history_row_prefers_explicit_from_account(self):
        adapter = SettledProductTransactionAdapter()

        row = adapter.build_trade_history_row(
            {
                'transaction_id': 12,
                'side': 'sell_token_0',
                'amount_0_in': '5',
                'amount_0_out': None,
                'amount_1_in': None,
                'amount_1_out': '6',
                'trade_time_ms': 5678,
                'from_account': 'chain-b:owner-b',
            }
        )

        self.assertEqual(row['transaction_type'], 'SellToken0')
        self.assertEqual(row['from_account'], 'chain-b:owner-b')

    def test_build_liquidity_history_row_maps_add_and_remove_shapes(self):
        adapter = SettledProductTransactionAdapter()

        add_row = adapter.build_liquidity_history_row(
            {
                'transaction_id': 21,
                'change_type': 'add_liquidity',
                'amount_0_delta': '3',
                'amount_1_delta': '4',
                'liquidity_delta': '5',
                'event_time_ms': 2000,
                'owner': 'owner-a@chain-a',
            }
        )
        remove_row = adapter.build_liquidity_history_row(
            {
                'transaction_id': 22,
                'change_type': 'remove_liquidity',
                'amount_0_delta': '7',
                'amount_1_delta': '8',
                'liquidity_delta': '9',
                'event_time_ms': 3000,
                'owner': 'owner-b@chain-b',
            }
        )

        self.assertEqual(
            add_row,
            {
                'transaction_id': 21,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '3',
                'amount_0_out': None,
                'amount_1_in': '4',
                'amount_1_out': None,
                'liquidity': '5',
                'created_at': 2000,
                'from_account': 'chain-a:owner-a',
            },
        )
        self.assertEqual(
            remove_row,
            {
                'transaction_id': 22,
                'transaction_type': 'RemoveLiquidity',
                'amount_0_in': None,
                'amount_0_out': '7',
                'amount_1_in': None,
                'amount_1_out': '8',
                'liquidity': '9',
                'created_at': 3000,
                'from_account': 'chain-b:owner-b',
            },
        )

    def test_owner_and_account_converters_tolerate_invalid_shapes(self):
        adapter = SettledProductTransactionAdapter()

        self.assertEqual(
            adapter.settled_owner_from_public_owner('chain-a:owner-a'),
            'owner-a@chain-a',
        )
        self.assertEqual(
            adapter.public_owner_from_settled_owner('owner-a@chain-a'),
            'chain-a:owner-a',
        )
        self.assertIsNone(adapter.public_owner_from_settled_owner('invalid-owner'))
        self.assertEqual(
            adapter.account_payload_to_string({'chain_id': 'chain-a', 'owner': 'owner-a'}),
            'chain-a:owner-a',
        )
        self.assertIsNone(adapter.account_payload_to_string({'chain_id': 'chain-a'}))
        self.assertIsNone(adapter.account_payload_to_string(None))


if __name__ == '__main__':
    unittest.main()
