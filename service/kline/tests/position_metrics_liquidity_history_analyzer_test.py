import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_liquidity_history_analyzer import PositionMetricsLiquidityHistoryAnalyzer  # noqa: E402


class PositionMetricsLiquidityHistoryAnalyzerTest(unittest.TestCase):
    def _build_analyzer(self):
        return PositionMetricsLiquidityHistoryAnalyzer(
            to_decimal=lambda value: None if value is None else Decimal(str(value)),
            to_attos=lambda value: int(Decimal(str(value))) if value is not None else None,
            from_attos=lambda value: Decimal(value) if value is not None else None,
            normalize_non_negative=lambda value: Decimal('0') if abs(value) <= Decimal('0.000000000001') else value,
            serialize_decimal=lambda value: format(value.normalize(), 'f'),
            split_protocol_fee_redeemable_attos=lambda **_kwargs: (0, 0),
            fee_numerator=997,
            fee_denominator=1000,
        )

    def test_history_liquidity_and_history_before(self):
        analyzer = self._build_analyzer()
        history = [
            {'transaction_type': 'AddLiquidity', 'liquidity': '2', 'created_at': 1, 'transaction_id': 1},
            {'transaction_type': 'RemoveLiquidity', 'liquidity': '1', 'created_at': 2, 'transaction_id': 2},
            {'transaction_type': 'AddLiquidity', 'liquidity': '4', 'created_at': 3, 'transaction_id': 3},
        ]

        self.assertEqual(analyzer.history_liquidity(history), Decimal('5'))
        self.assertEqual(
            analyzer.history_liquidity_before(history, history[-1]),
            Decimal('1'),
        )

    def test_build_estimated_metrics_from_liquidity_history(self):
        analyzer = self._build_analyzer()
        metrics = analyzer.build_estimated_metrics_from_liquidity_history(
            {
                'redeemable_amount0': '40',
                'redeemable_amount1': '80',
                'total_supply_live': '10',
            },
            liquidity_history=[
                {
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '2',
                    'amount_0_in': '20',
                    'amount_1_in': '40',
                    'created_at': 1,
                    'transaction_id': 1,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_type': 'SellToken0',
                    'amount_0_in': '10',
                    'created_at': 1,
                    'transaction_id': 1,
                },
            ],
            live_liquidity=Decimal('2'),
            history_liquidity=Decimal('2'),
        )

        self.assertEqual(metrics['metrics_status'], 'estimated_live_redeemable_with_history')
        self.assertEqual(metrics['principal_amount0'], '39.994')
        self.assertEqual(metrics['principal_amount1'], '80')
        self.assertEqual(metrics['fee_amount0'], '0.006')
        self.assertEqual(metrics['fee_amount1'], '0')


if __name__ == '__main__':
    unittest.main()
