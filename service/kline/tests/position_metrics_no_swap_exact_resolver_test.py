import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_no_swap_exact_resolver import PositionMetricsNoSwapExactResolver  # noqa: E402


class PositionMetricsNoSwapExactResolverTest(unittest.TestCase):
    def test_builds_exact_no_swap_metrics(self):
        resolver = PositionMetricsNoSwapExactResolver(
            serialize_decimal=lambda value: format(value.normalize(), 'f'),
        )
        decimal_module = __import__('decimal')

        result = resolver.resolve(
            {
                'metrics_status': 'partial_live_redeemable_only',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
            },
            redeemable_amount0=decimal_module.Decimal('40'),
            redeemable_amount1=decimal_module.Decimal('80'),
            blockers=[],
        )

        self.assertEqual(result['metrics_status'], 'exact_no_swap_history')
        self.assertTrue(result['exact_fee_supported'])
        self.assertTrue(result['exact_principal_supported'])
        self.assertEqual(result['principal_amount0'], '40')
        self.assertEqual(result['principal_amount1'], '80')
        self.assertEqual(result['fee_amount0'], '0')
        self.assertEqual(result['fee_amount1'], '0')
        self.assertEqual(result['protocol_fee_amount0'], '0')
        self.assertEqual(result['protocol_fee_amount1'], '0')
        self.assertEqual(result['computation_blockers'], [])
