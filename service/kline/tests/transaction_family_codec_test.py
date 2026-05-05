import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from transaction_family_codec import TransactionFamilyCodec  # noqa: E402


class TransactionFamilyCodecTest(unittest.TestCase):
    def test_trade_side_and_transaction_type_round_trip(self):
        codec = TransactionFamilyCodec()

        self.assertEqual(codec.trade_side_from_transaction_type('BuyToken0'), 'buy_token_0')
        self.assertEqual(codec.trade_side_from_transaction_type('SellToken0'), 'sell_token_0')
        self.assertEqual(codec.transaction_type_from_trade_side('buy_token_0'), 'BuyToken0')
        self.assertEqual(codec.transaction_type_from_trade_side('sell_token_0'), 'SellToken0')

    def test_liquidity_change_type_and_transaction_type_round_trip(self):
        codec = TransactionFamilyCodec()

        self.assertEqual(codec.liquidity_change_type_from_transaction_type('AddLiquidity'), 'add_liquidity')
        self.assertEqual(codec.liquidity_change_type_from_transaction_type('RemoveLiquidity'), 'remove_liquidity')
        self.assertEqual(codec.transaction_type_from_liquidity_change_type('add_liquidity'), 'AddLiquidity')
        self.assertEqual(codec.transaction_type_from_liquidity_change_type('remove_liquidity'), 'RemoveLiquidity')

    def test_trade_direction_respects_token_reversal(self):
        codec = TransactionFamilyCodec()

        self.assertEqual(codec.trade_direction('BuyToken0', token_reversed=False), 'Buy')
        self.assertEqual(codec.trade_direction('BuyToken0', token_reversed=True), 'Sell')
        self.assertEqual(codec.trade_direction('SellToken0', token_reversed=False), 'Sell')
        self.assertEqual(codec.trade_direction('SellToken0', token_reversed=True), 'Buy')


if __name__ == '__main__':
    unittest.main()
