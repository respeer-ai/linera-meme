import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_estimated_fallback_resolver import PositionMetricsEstimatedFallbackResolver  # noqa: E402
from position_metrics_history_evaluation import PositionMetricsHistoryEvaluation  # noqa: E402
from position_metrics_history_semantic_resolver import PositionMetricsHistorySemanticResolver  # noqa: E402
from position_metrics_no_swap_exact_resolver import PositionMetricsNoSwapExactResolver  # noqa: E402


class PositionMetricsHistorySemanticResolverTest(unittest.TestCase):
    def test_returns_partial_metrics_when_history_is_missing(self):
        resolver = PositionMetricsHistorySemanticResolver(
            no_swap_exact_resolver=PositionMetricsNoSwapExactResolver(
                serialize_decimal=lambda value: format(value.normalize(), 'f'),
            ),
            estimated_fallback_resolver=PositionMetricsEstimatedFallbackResolver(
                build_estimated_metrics_from_liquidity_history=lambda partial_metrics, **_kwargs: partial_metrics,
            ),
        )

        result = resolver.resolve(
            PositionMetricsHistoryEvaluation(
                partial_metrics={
                    'metrics_status': 'partial_live_redeemable_only',
                    'exact_fee_supported': False,
                    'exact_principal_supported': False,
                    'computation_blockers': [],
                },
                blockers=['missing_liquidity_history'],
                liquidity_history=[],
                pool_transaction_history=None,
                live_liquidity=None,
                history_liquidity=None,
                redeemable_amount0=None,
                redeemable_amount1=None,
                swap_exact_metrics=None,
                swap_blockers=[],
                has_pool_swap_history=False,
            ),
        )

        self.assertEqual(result['metrics_status'], 'partial_live_redeemable_only')
        self.assertEqual(result['computation_blockers'], ['missing_liquidity_history'])

    def test_marks_exact_when_no_blockers_and_no_swap_history(self):
        resolver = PositionMetricsHistorySemanticResolver(
            no_swap_exact_resolver=PositionMetricsNoSwapExactResolver(
                serialize_decimal=lambda value: format(value.normalize(), 'f'),
            ),
            estimated_fallback_resolver=PositionMetricsEstimatedFallbackResolver(
                build_estimated_metrics_from_liquidity_history=lambda partial_metrics, **_kwargs: partial_metrics,
            ),
        )

        decimal_module = __import__('decimal')
        result = resolver.resolve(
            PositionMetricsHistoryEvaluation(
                partial_metrics={
                'metrics_status': 'partial_live_redeemable_only',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'computation_blockers': [],
                },
                blockers=[],
                liquidity_history=[{'transaction_type': 'AddLiquidity'}],
                pool_transaction_history=[],
                live_liquidity=decimal_module.Decimal('2'),
                history_liquidity=decimal_module.Decimal('2'),
                redeemable_amount0=decimal_module.Decimal('40'),
                redeemable_amount1=decimal_module.Decimal('80'),
                swap_exact_metrics=None,
                swap_blockers=[],
                has_pool_swap_history=False,
            ),
        )

        self.assertEqual(result['metrics_status'], 'exact_no_swap_history')
        self.assertTrue(result['exact_fee_supported'])
        self.assertTrue(result['exact_principal_supported'])
        self.assertEqual(result['principal_amount0'], '40')
        self.assertEqual(result['principal_amount1'], '80')
        self.assertEqual(result['computation_blockers'], [])

    def test_uses_estimated_metrics_when_swap_history_prevents_exact_result(self):
        estimated = {
            'metrics_status': 'estimated_live_redeemable_with_history',
            'principal_amount0': '10',
            'principal_amount1': '20',
            'fee_amount0': '1',
            'fee_amount1': '2',
            'protocol_fee_amount0': '0',
            'protocol_fee_amount1': '0',
        }
        resolver = PositionMetricsHistorySemanticResolver(
            no_swap_exact_resolver=PositionMetricsNoSwapExactResolver(
                serialize_decimal=lambda value: format(value.normalize(), 'f'),
            ),
            estimated_fallback_resolver=PositionMetricsEstimatedFallbackResolver(
                build_estimated_metrics_from_liquidity_history=lambda partial_metrics, **_kwargs: {
                    **partial_metrics,
                    **estimated,
                },
            ),
        )

        decimal_module = __import__('decimal')
        result = resolver.resolve(
            PositionMetricsHistoryEvaluation(
                partial_metrics={
                'metrics_status': 'partial_live_redeemable_only',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'computation_blockers': [],
                },
                blockers=[],
                liquidity_history=[{'transaction_type': 'AddLiquidity'}],
                pool_transaction_history=[{'transaction_type': 'BuyToken0'}],
                live_liquidity=decimal_module.Decimal('2'),
                history_liquidity=decimal_module.Decimal('2'),
                redeemable_amount0=decimal_module.Decimal('40'),
                redeemable_amount1=decimal_module.Decimal('80'),
                swap_exact_metrics=None,
                swap_blockers=['pool_history_bootstrap_supply_unknown'],
                has_pool_swap_history=True,
            ),
        )

        self.assertEqual(result['metrics_status'], 'estimated_live_redeemable_with_history')
        self.assertIn('pool_has_swap_history_after_position_open', result['computation_blockers'])
        self.assertIn('pool_history_bootstrap_supply_unknown', result['computation_blockers'])
        self.assertIn('uniswap_v2_fee_split_not_supported_yet', result['computation_blockers'])
