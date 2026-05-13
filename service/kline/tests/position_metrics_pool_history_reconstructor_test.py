import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_pool_history_reconstructor import PositionMetricsPoolHistoryReconstructor  # noqa: E402


class PositionMetricsPoolHistoryReconstructorTest(unittest.TestCase):
    def test_reconstruct_returns_missing_history_blocker(self):
        reconstructor = PositionMetricsPoolHistoryReconstructor(
            to_attos=lambda value: value,
            swap_expected_out_attos=lambda *_args, **_kwargs: None,
            swap_out_within_tolerance=lambda *_args, **_kwargs: False,
            infer_hidden_swap_before_batch=lambda *_args, **_kwargs: None,
            apply_recorded_swap_attos=lambda *_args, **_kwargs: (0, 0),
            sqrt_attos_product=lambda *_args, **_kwargs: None,
            mint_fee_attos=lambda *_args, **_kwargs: 0,
            attos_within_tolerance=lambda *_args, **_kwargs: False,
        )

        effective_history, states, blockers = reconstructor.reconstruct(
            [],
            virtual_initial_liquidity=False,
        )

        self.assertIsNone(effective_history)
        self.assertIsNone(states)
        self.assertEqual(blockers, ['missing_pool_transaction_history'])

    def test_reconstruct_tracks_bootstrap_add_liquidity_state(self):
        reconstructor = PositionMetricsPoolHistoryReconstructor(
            to_attos=lambda value: 0 if value is None else int(value),
            swap_expected_out_attos=lambda *_args, **_kwargs: None,
            swap_out_within_tolerance=lambda *_args, **_kwargs: False,
            infer_hidden_swap_before_batch=lambda *_args, **_kwargs: None,
            apply_recorded_swap_attos=lambda tx_type, reserve0, reserve1, **kwargs: (reserve0, reserve1),
            sqrt_attos_product=lambda a0, a1: 20 if (a0, a1) == (20, 20) else None,
            mint_fee_attos=lambda *_args, **_kwargs: 0,
            attos_within_tolerance=lambda left, right: left == right,
        )

        effective_history, states, blockers = reconstructor.reconstruct(
            [
                {
                    'transaction_id': 1,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:owner-a',
                    'amount_0_in': 20,
                    'amount_1_in': 20,
                    'amount_0_out': 0,
                    'amount_1_out': 0,
                    'liquidity': 20,
                    'created_at': 100,
                },
            ],
            virtual_initial_liquidity=False,
        )

        self.assertEqual(blockers, [])
        self.assertEqual(len(effective_history), 1)
        self.assertEqual(states[0]['reserve0_after'], 20)
        self.assertEqual(states[0]['reserve1_after'], 20)
        self.assertEqual(states[0]['total_supply_after'], 20)


if __name__ == '__main__':
    unittest.main()
