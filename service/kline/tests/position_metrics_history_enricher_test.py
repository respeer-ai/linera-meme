import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_history_enricher import PositionMetricsHistoryEnricher  # noqa: E402
from position_metrics_estimated_fallback_resolver import PositionMetricsEstimatedFallbackResolver  # noqa: E402
from position_metrics_history_semantic_resolver import PositionMetricsHistorySemanticResolver  # noqa: E402
from position_metrics_no_swap_exact_resolver import PositionMetricsNoSwapExactResolver  # noqa: E402


class PositionMetricsHistoryEnricherTest(unittest.TestCase):
    def test_enrich_marks_exact_when_no_swap_history_and_no_blockers(self):
        enricher = PositionMetricsHistoryEnricher(
            to_decimal=lambda value: None if value is None else __import__('decimal').Decimal(str(value)),
            history_liquidity=lambda history: __import__('decimal').Decimal('2.0'),
            try_enrich_metrics_with_swap_history=lambda *_args, **_kwargs: (None, []),
            semantic_resolver=PositionMetricsHistorySemanticResolver(
                no_swap_exact_resolver=PositionMetricsNoSwapExactResolver(
                    serialize_decimal=lambda value: format(value.normalize(), 'f'),
                ),
                estimated_fallback_resolver=PositionMetricsEstimatedFallbackResolver(
                    build_estimated_metrics_from_liquidity_history=lambda partial_metrics, **_kwargs: partial_metrics,
                ),
            ),
        )

        result = enricher.enrich(
            {
                'position_liquidity_live': '2.0',
                'redeemable_amount0': '40',
                'redeemable_amount1': '80',
                'metrics_status': 'partial_live_redeemable_only',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'computation_blockers': [],
            },
            liquidity_history=[{'transaction_type': 'AddLiquidity', 'liquidity': '2.0'}],
            pool_transaction_history=[],
            pool_swap_count_since_open=0,
            owner_is_fee_to=False,
        )

        self.assertEqual(result['metrics_status'], 'exact_no_swap_history')
        self.assertTrue(result['exact_fee_supported'])
        self.assertTrue(result['exact_principal_supported'])
        self.assertEqual(result['principal_amount0'], '40')
        self.assertEqual(result['principal_amount1'], '80')
        self.assertEqual(result['computation_blockers'], [])

    def test_enrich_adds_swap_blockers_and_uses_estimated_metrics_when_exact_fails(self):
        estimated = {
            'metrics_status': 'estimated_live_redeemable_with_history',
            'principal_amount0': '10',
            'principal_amount1': '20',
            'fee_amount0': '1',
            'fee_amount1': '2',
            'protocol_fee_amount0': '0',
            'protocol_fee_amount1': '0',
            'computation_blockers': [],
        }

        enricher = PositionMetricsHistoryEnricher(
            to_decimal=lambda value: None if value is None else __import__('decimal').Decimal(str(value)),
            history_liquidity=lambda history: __import__('decimal').Decimal('2.0'),
            try_enrich_metrics_with_swap_history=lambda *_args, **_kwargs: (None, ['pool_history_bootstrap_supply_unknown']),
            semantic_resolver=PositionMetricsHistorySemanticResolver(
                no_swap_exact_resolver=PositionMetricsNoSwapExactResolver(
                    serialize_decimal=lambda value: format(value.normalize(), 'f'),
                ),
                estimated_fallback_resolver=PositionMetricsEstimatedFallbackResolver(
                    build_estimated_metrics_from_liquidity_history=lambda partial_metrics, **_kwargs: {
                        **partial_metrics,
                        **estimated,
                    },
                ),
            ),
        )

        result = enricher.enrich(
            {
                'position_liquidity_live': '2.0',
                'redeemable_amount0': '40',
                'redeemable_amount1': '80',
                'metrics_status': 'partial_live_redeemable_only',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'computation_blockers': [],
            },
            liquidity_history=[{'transaction_type': 'AddLiquidity', 'liquidity': '2.0'}],
            pool_transaction_history=[{'transaction_type': 'BuyToken0'}],
            pool_swap_count_since_open=1,
            owner_is_fee_to=False,
        )

        self.assertEqual(result['metrics_status'], 'estimated_live_redeemable_with_history')
        self.assertIn('pool_has_swap_history_after_position_open', result['computation_blockers'])
        self.assertIn('pool_history_bootstrap_supply_unknown', result['computation_blockers'])
        self.assertIn('uniswap_v2_fee_split_not_supported_yet', result['computation_blockers'])


if __name__ == '__main__':
    unittest.main()
