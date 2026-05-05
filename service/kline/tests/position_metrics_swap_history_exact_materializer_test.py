import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_swap_history_exact_materializer import PositionMetricsSwapHistoryExactMaterializer  # noqa: E402


class PositionMetricsSwapHistoryExactMaterializerTest(unittest.TestCase):
    def test_formats_exact_metrics_when_materialization_succeeds(self):
        materializer = PositionMetricsSwapHistoryExactMaterializer(
            from_attos=lambda value: Decimal(value) / Decimal(1) if value is not None else None,
            normalize_non_negative=lambda value: Decimal('0') if abs(value) <= Decimal('0.000000000001') else value,
            serialize_decimal=lambda value: format(value.normalize(), 'f'),
        )
        payload = {'computation_blockers': ['stale']}

        metrics, blockers = materializer.materialize(
            payload,
            validation_context={
                'liquidity_basis_attos': 2,
                'current_total_supply_attos': 4,
                'fee_free_state': {'reserve0': 80, 'reserve1': 160},
                'redeemable_amount0': Decimal('40'),
                'redeemable_amount1': Decimal('80'),
                'protocol_fee_amount0': Decimal('0'),
                'protocol_fee_amount1': Decimal('0'),
            },
        )

        self.assertEqual(blockers, [])
        self.assertIs(metrics, payload)
        self.assertEqual(metrics['metrics_status'], 'exact_swap_history_no_post_open_liquidity_changes')
        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertEqual(metrics['principal_amount0'], '40')
        self.assertEqual(metrics['principal_amount1'], '80')
        self.assertEqual(metrics['fee_amount0'], '0')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['computation_blockers'], [])
