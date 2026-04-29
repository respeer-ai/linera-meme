import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_warning_applier import PositionMetricsWarningApplier  # noqa: E402


class PositionMetricsWarningApplierTest(unittest.TestCase):
    def test_apply_marks_estimated_values_when_exact_fee_unsupported(self):
        metrics = PositionMetricsWarningApplier().apply({
            'exact_fee_supported': False,
            'exact_principal_supported': False,
            'computation_blockers': [],
            'fee_amount0': None,
            'fee_amount1': None,
            'protocol_fee_amount0': None,
            'protocol_fee_amount1': None,
            'value_warning_codes': [],
            'value_warning_message': None,
        })

        self.assertEqual(metrics['value_warning_codes'], ['estimated_values'])
        self.assertIn('estimated', metrics['value_warning_message'])
        self.assertEqual(metrics['fee_amount0'], '0')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0')
        self.assertEqual(metrics['protocol_fee_amount1'], '0')

    def test_apply_adds_gap_blocker_for_actionable_gap_basis(self):
        metrics = PositionMetricsWarningApplier().apply(
            {
                'exact_fee_supported': True,
                'exact_principal_supported': True,
                'computation_blockers': [],
                'fee_amount0': '1',
                'fee_amount1': '2',
                'protocol_fee_amount0': '0',
                'protocol_fee_amount1': '0',
                'value_warning_codes': [],
                'value_warning_message': None,
            },
            pool_history_gap_summary={
                'has_internal_gaps': True,
                'basis': 'archive_reconciliation',
            },
        )

        self.assertIn('pool_history_has_internal_gaps', metrics['computation_blockers'])
        self.assertFalse(metrics['exact_fee_supported'])
        self.assertFalse(metrics['exact_principal_supported'])
        self.assertEqual(metrics['value_warning_codes'], ['estimated_values'])
        self.assertIn('incomplete history', metrics['value_warning_message'])


if __name__ == '__main__':
    unittest.main()
