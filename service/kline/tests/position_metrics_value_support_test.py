import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from position_metrics_value_support import PositionMetricsValueSupport


class PositionMetricsValueSupportTest(unittest.TestCase):
    def setUp(self):
        self.value_support = PositionMetricsValueSupport(
            attos_scale=10 ** 18,
            display_quantum=Decimal('0.000000000000000001'),
            epsilon=Decimal('0.000000000001'),
            liquidity_mint_tolerance_attos=100,
            swap_out_tolerance_attos=1,
        )

    def test_to_attos_truncates_beyond_amount_precision(self):
        self.assertEqual(
            self.value_support.to_attos('1.0000000000000000019'),
            1000000000000000001,
        )


if __name__ == '__main__':
    unittest.main()
