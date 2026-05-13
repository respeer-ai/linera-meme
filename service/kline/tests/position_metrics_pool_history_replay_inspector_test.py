import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_pool_history_replay_inspector import PositionMetricsPoolHistoryReplayInspector  # noqa: E402


class PositionMetricsPoolHistoryReplayInspectorTest(unittest.TestCase):
    def test_inspect_returns_missing_history_failure(self):
        inspector = PositionMetricsPoolHistoryReplayInspector(
            to_attos=lambda value: value,
            swap_expected_out_attos=lambda *_args, **_kwargs: None,
            swap_out_within_tolerance=lambda *_args, **_kwargs: False,
            infer_hidden_swap_before_batch=lambda *_args, **_kwargs: None,
            apply_recorded_swap_attos=lambda *_args, **_kwargs: (0, 0),
            sqrt_attos_product=lambda *_args, **_kwargs: None,
            mint_fee_attos=lambda *_args, **_kwargs: 0,
            attos_within_tolerance=lambda *_args, **_kwargs: False,
            serialize_attos_debug=lambda value: None if value is None else str(value),
        )

        audit = inspector.inspect(
            [],
            virtual_initial_liquidity=False,
            swap_out_tolerance_attos=1,
        )

        self.assertFalse(audit['ok'])
        self.assertEqual(audit['processed_count'], 0)
        self.assertEqual(audit['blockers'], ['missing_pool_transaction_history'])
        self.assertEqual(audit['first_failure']['reason'], 'missing_pool_transaction_history')


if __name__ == '__main__':
    unittest.main()
