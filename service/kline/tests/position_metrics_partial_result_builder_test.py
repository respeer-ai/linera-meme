import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_partial_result_builder import PositionMetricsPartialResultBuilder  # noqa: E402


class PositionMetricsPartialResultBuilderTest(unittest.TestCase):
    def test_build_initializes_partial_metrics_shape(self):
        result = PositionMetricsPartialResultBuilder().build(
            {
                'liquidity': '1.23',
                'amount0': '40',
                'amount1': '80',
            },
            '5.0',
            True,
        )

        self.assertEqual(result['position_liquidity_live'], '1.23')
        self.assertEqual(result['total_supply_live'], '5.0')
        self.assertEqual(result['redeemable_amount0'], '40')
        self.assertEqual(result['redeemable_amount1'], '80')
        self.assertTrue(result['virtual_initial_liquidity'])
        self.assertEqual(result['metrics_status'], 'partial_live_redeemable_only')
        self.assertFalse(result['exact_fee_supported'])
        self.assertFalse(result['exact_principal_supported'])
        self.assertEqual(result['fee_amount0'], '0')
        self.assertEqual(result['fee_amount1'], '0')
        self.assertEqual(result['protocol_fee_amount0'], '0')
        self.assertEqual(result['protocol_fee_amount1'], '0')
        self.assertEqual(result['computation_blockers'], [])
        self.assertEqual(result['value_warning_codes'], [])
        self.assertIsNone(result['value_warning_message'])


if __name__ == '__main__':
    unittest.main()
