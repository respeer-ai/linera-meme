import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_swap_history_precheck import PositionMetricsSwapHistoryPrecheck  # noqa: E402


class PositionMetricsSwapHistoryPrecheckTest(unittest.TestCase):
    def test_returns_missing_redeemable_blocker(self):
        precheck = PositionMetricsSwapHistoryPrecheck(
            to_decimal=lambda value: None if value is None else Decimal(str(value)),
            history_liquidity=lambda history: Decimal('0'),
        )

        context, blockers = precheck.check(
            {
                'position_liquidity': '1',
                'current_total_supply': '2',
                'redeemable_amount0': None,
                'redeemable_amount1': '1',
            },
            liquidity_history=[{'transaction_type': 'AddLiquidity'}],
        )

        self.assertIsNone(context)
        self.assertEqual(blockers, ['missing_projected_redeemable_amounts'])
