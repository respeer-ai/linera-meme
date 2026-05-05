import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_fee_to_opening_mint_resolver import PositionMetricsFeeToOpeningMintResolver  # noqa: E402


class PositionMetricsFeeToOpeningMintResolverTest(unittest.TestCase):
    def test_returns_liquidity_history_mismatch_when_non_fee_to_excess_liquidity_exists(self):
        resolver = PositionMetricsFeeToOpeningMintResolver(
            history_liquidity_before=lambda *_args, **_kwargs: Decimal('0'),
            split_protocol_fee_redeemable_attos=lambda **_kwargs: (0, 0),
            from_attos=lambda value: Decimal(value) if value is not None else None,
            epsilon=Decimal('0.000000000001'),
        )

        context, blockers = resolver.resolve(
            liquidity_history=[{'transaction_id': 10, 'transaction_type': 'AddLiquidity', 'created_at': 100}],
            latest_position_tx={'transaction_id': 10, 'transaction_type': 'AddLiquidity', 'created_at': 100},
            owner_is_fee_to=False,
            precheck_context={
                'live_liquidity': Decimal('3'),
                'history_liquidity': Decimal('2'),
                'redeemable_amount0': Decimal('40'),
                'redeemable_amount1': Decimal('80'),
            },
        )

        self.assertIsNone(context)
        self.assertEqual(blockers, ['liquidity_history_mismatch'])
