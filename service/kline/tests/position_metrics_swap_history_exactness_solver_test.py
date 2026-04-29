import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_swap_history_exactness_solver import PositionMetricsSwapHistoryExactnessSolver  # noqa: E402


class PositionMetricsSwapHistoryExactnessSolverTest(unittest.TestCase):
    def test_solve_returns_missing_redeemable_blocker(self):
        solver = PositionMetricsSwapHistoryExactnessSolver(
            to_decimal=lambda value: None if value is None else Decimal(str(value)),
            history_liquidity=lambda history: Decimal('0'),
            reconstruct_pool_history=lambda history, **_kwargs: ([], [], []),
            history_liquidity_before=lambda *_args, **_kwargs: Decimal('0'),
            split_protocol_fee_redeemable_attos=lambda **_kwargs: (0, 0),
            from_attos=lambda value: Decimal(value) if value is not None else None,
            effective_total_supply_attos_from_state=lambda state: 0,
            attos_within_tolerance=lambda *_args, **_kwargs: True,
            simulate_fee_free_from_open_state=lambda *_args, **_kwargs: ({'reserve0': 0, 'reserve1': 0}, []),
            normalize_non_negative=lambda value: value,
            serialize_decimal=lambda value: format(value.normalize(), 'f'),
            to_attos=lambda value: 0 if value is not None else None,
            epsilon=Decimal('0.000000000001'),
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
            to_decimal=lambda value: None if value is None else Decimal(str(value)),
            history_liquidity=lambda history: Decimal('2'),
            reconstruct_pool_history=lambda history, **_kwargs: (
                [{'transaction_id': 10, 'transaction_type': 'AddLiquidity', 'created_at': 100}],
                [{'transaction_id': 10, 'created_at': 100, 'total_supply_after': 4, 'reserve0_after': 80, 'reserve1_after': 160, 'k_last_after': 0}],
                [],
            ),
            history_liquidity_before=lambda *_args, **_kwargs: Decimal('0'),
            split_protocol_fee_redeemable_attos=lambda **_kwargs: (0, 0),
            from_attos=lambda value: Decimal(value) / Decimal(1) if value is not None else None,
            effective_total_supply_attos_from_state=lambda state: 4,
            attos_within_tolerance=lambda *_args, **_kwargs: True,
            simulate_fee_free_from_open_state=lambda *_args, **_kwargs: ({'reserve0': 80, 'reserve1': 160}, []),
            normalize_non_negative=lambda value: Decimal('0') if abs(value) <= Decimal('0.000000000001') else value,
            serialize_decimal=lambda value: format(value.normalize(), 'f'),
            to_attos=lambda value: int(Decimal(str(value))),
            epsilon=Decimal('0.000000000001'),
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
