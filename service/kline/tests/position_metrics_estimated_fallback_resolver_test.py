import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_estimated_fallback_resolver import PositionMetricsEstimatedFallbackResolver  # noqa: E402


class PositionMetricsEstimatedFallbackResolverTest(unittest.TestCase):
    def test_builds_estimated_metrics_and_preserves_blockers(self):
        resolver = PositionMetricsEstimatedFallbackResolver(
            build_estimated_metrics_from_liquidity_history=lambda partial_metrics, **_kwargs: {
                **partial_metrics,
                'metrics_status': 'estimated_live_redeemable_with_history',
                'principal_amount0': '10',
                'principal_amount1': '20',
            },
        )

        result = resolver.resolve(
            {
                'metrics_status': 'partial_live_redeemable_only',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
            },
            blockers=['pool_has_swap_history_after_position_open'],
            liquidity_history=[{'transaction_type': 'AddLiquidity'}],
            pool_transaction_history=[{'transaction_type': 'BuyToken0'}],
            live_liquidity=__import__('decimal').Decimal('2'),
            history_liquidity=__import__('decimal').Decimal('2'),
        )

        self.assertEqual(result['metrics_status'], 'estimated_live_redeemable_with_history')
        self.assertEqual(result['principal_amount0'], '10')
        self.assertEqual(result['principal_amount1'], '20')
        self.assertEqual(
            result['computation_blockers'],
            ['pool_has_swap_history_after_position_open'],
        )
