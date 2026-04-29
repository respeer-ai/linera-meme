import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_swap_math_support import PositionMetricsSwapMathSupport  # noqa: E402


class PositionMetricsSwapMathSupportTest(unittest.TestCase):
    def _build_support(self):
        return PositionMetricsSwapMathSupport(
            to_attos=lambda value: None if value is None else int(Decimal(str(value))),
            from_attos=lambda value: None if value is None else Decimal(value),
            swap_fee_numerator=997,
            swap_fee_denominator=1000,
            swap_out_tolerance_attos=1,
        )

    def test_swap_expected_out_and_apply_recorded_swap(self):
        support = self._build_support()

        amount0_out = support.swap_expected_out_attos('BuyToken0', 1000, 1000, 0, 100)
        reserve0, reserve1 = support.apply_recorded_swap_attos(
            'BuyToken0',
            1000,
            1000,
            amount0_in=0,
            amount0_out=amount0_out,
            amount1_in=100,
            amount1_out=0,
        )

        self.assertEqual(amount0_out, 90)
        self.assertEqual((reserve0, reserve1), (910, 1100))

    def test_mint_fee_attos_zero_when_no_growth(self):
        support = self._build_support()
        self.assertEqual(support.mint_fee_attos(1000, 1000, 1000, 1000), 0)

    def test_infer_hidden_swap_before_batch_returns_none_without_following_swap(self):
        support = self._build_support()
        self.assertIsNone(
            support.infer_hidden_swap_before_batch(
                1000,
                1000,
                [{'transaction_type': 'BuyToken0', 'created_at': 1}],
                0,
            )
        )


if __name__ == '__main__':
    unittest.main()
