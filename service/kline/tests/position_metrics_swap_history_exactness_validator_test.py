import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_swap_history_alignment_checker import PositionMetricsSwapHistoryAlignmentChecker  # noqa: E402
from position_metrics_fee_to_opening_mint_resolver import PositionMetricsFeeToOpeningMintResolver  # noqa: E402
from position_metrics_swap_history_precheck import PositionMetricsSwapHistoryPrecheck  # noqa: E402
from position_metrics_swap_history_exactness_validator import PositionMetricsSwapHistoryExactnessValidator  # noqa: E402


class ReplayEntrypointStub:
    def __init__(self, *, reconstruct_result, total_supply_after, fee_free_result):
        self.reconstruct_result = reconstruct_result
        self.total_supply_after = total_supply_after
        self.fee_free_result = fee_free_result

    def reconstruct_pool_history(self, *_args, **_kwargs):
        return self.reconstruct_result

    def effective_total_supply_attos_from_state(self, _state):
        return self.total_supply_after

    def simulate_fee_free_from_open_state(self, *_args, **_kwargs):
        return self.fee_free_result


class PositionMetricsSwapHistoryExactnessValidatorTest(unittest.TestCase):
    def test_returns_missing_redeemable_blocker(self):
        validator = PositionMetricsSwapHistoryExactnessValidator(
            precheck=PositionMetricsSwapHistoryPrecheck(
                to_decimal=lambda value: None if value is None else Decimal(str(value)),
                history_liquidity=lambda history: Decimal('0'),
            ),
            alignment_checker=PositionMetricsSwapHistoryAlignmentChecker(
                replay_entrypoint=ReplayEntrypointStub(
                    reconstruct_result=([], [], []),
                    total_supply_after=0,
                    fee_free_result=({'reserve0': 0, 'reserve1': 0}, []),
                ),
                fee_to_opening_mint_resolver=PositionMetricsFeeToOpeningMintResolver(
                    history_liquidity_before=lambda *_args, **_kwargs: Decimal('0'),
                    split_protocol_fee_redeemable_attos=lambda **_kwargs: (0, 0),
                    from_attos=lambda value: Decimal(value) if value is not None else None,
                    epsilon=Decimal('0.000000000001'),
                ),
                attos_within_tolerance=lambda *_args, **_kwargs: True,
                to_attos=lambda value: 0 if value is not None else None,
            ),
        )

        context, blockers = validator.validate(
            {
                'position_liquidity': '1',
                'current_total_supply': '2',
                'redeemable_amount0': None,
                'redeemable_amount1': '1',
                'virtual_initial_liquidity': False,
            },
            liquidity_history=[{'transaction_type': 'AddLiquidity'}],
            pool_transaction_history=[],
            owner_receives_protocol_fees=False,
        )

        self.assertIsNone(context)
        self.assertEqual(blockers, ['missing_projected_redeemable_amounts'])
