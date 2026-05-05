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
from position_metrics_swap_history_exact_materializer import PositionMetricsSwapHistoryExactMaterializer  # noqa: E402
from position_metrics_swap_history_precheck import PositionMetricsSwapHistoryPrecheck  # noqa: E402
from position_metrics_swap_history_exactness_solver import PositionMetricsSwapHistoryExactnessSolver  # noqa: E402
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


class PositionMetricsSwapHistoryExactnessSolverTest(unittest.TestCase):
    def test_solve_returns_missing_redeemable_blocker(self):
        solver = PositionMetricsSwapHistoryExactnessSolver(
            validator=PositionMetricsSwapHistoryExactnessValidator(
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
            ),
            materializer=PositionMetricsSwapHistoryExactMaterializer(
                from_attos=lambda value: Decimal(value) if value is not None else None,
                normalize_non_negative=lambda value: value,
                serialize_decimal=lambda value: format(value.normalize(), 'f'),
            ),
        )

        metrics, blockers = solver.solve(
            {
                'position_liquidity_live': '1',
                'total_supply_live': '2',
                'redeemable_amount0': None,
                'redeemable_amount1': '1',
                'virtual_initial_liquidity': False,
            },
            liquidity_history=[{'transaction_type': 'AddLiquidity'}],
            pool_transaction_history=[],
            owner_is_fee_to=False,
        )

        self.assertIsNone(metrics)
        self.assertEqual(blockers, ['missing_live_redeemable_amounts'])

    def test_solve_formats_exact_metrics_when_simulation_succeeds(self):
        solver = PositionMetricsSwapHistoryExactnessSolver(
            validator=PositionMetricsSwapHistoryExactnessValidator(
                precheck=PositionMetricsSwapHistoryPrecheck(
                    to_decimal=lambda value: None if value is None else Decimal(str(value)),
                    history_liquidity=lambda history: Decimal('2'),
                ),
                alignment_checker=PositionMetricsSwapHistoryAlignmentChecker(
                    replay_entrypoint=ReplayEntrypointStub(
                        reconstruct_result=(
                            [{'transaction_id': 10, 'transaction_type': 'AddLiquidity', 'created_at': 100}],
                            [{'transaction_id': 10, 'created_at': 100, 'total_supply_after': 4, 'reserve0_after': 80, 'reserve1_after': 160, 'k_last_after': 0}],
                            [],
                        ),
                        total_supply_after=4,
                        fee_free_result=({'reserve0': 80, 'reserve1': 160}, []),
                    ),
                    fee_to_opening_mint_resolver=PositionMetricsFeeToOpeningMintResolver(
                        history_liquidity_before=lambda *_args, **_kwargs: Decimal('0'),
                        split_protocol_fee_redeemable_attos=lambda **_kwargs: (0, 0),
                        from_attos=lambda value: Decimal(value) / Decimal(1) if value is not None else None,
                        epsilon=Decimal('0.000000000001'),
                    ),
                    attos_within_tolerance=lambda *_args, **_kwargs: True,
                    to_attos=lambda value: int(Decimal(str(value))),
                ),
            ),
            materializer=PositionMetricsSwapHistoryExactMaterializer(
                from_attos=lambda value: Decimal(value) / Decimal(1) if value is not None else None,
                normalize_non_negative=lambda value: Decimal('0') if abs(value) <= Decimal('0.000000000001') else value,
                serialize_decimal=lambda value: format(value.normalize(), 'f'),
            ),
        )

        payload = {
            'position_liquidity_live': '2',
            'total_supply_live': '4',
            'redeemable_amount0': '40',
            'redeemable_amount1': '80',
            'virtual_initial_liquidity': False,
            'computation_blockers': ['stale'],
        }
        metrics, blockers = solver.solve(
            payload,
            liquidity_history=[{'transaction_id': 10, 'transaction_type': 'AddLiquidity', 'created_at': 100}],
            pool_transaction_history=[{'transaction_id': 10, 'transaction_type': 'AddLiquidity', 'created_at': 100}],
            owner_is_fee_to=False,
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


if __name__ == '__main__':
    unittest.main()
