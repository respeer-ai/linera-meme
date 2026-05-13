import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_warning_applier import PositionMetricsWarningApplier  # noqa: E402


class PositionMetricsWarningApplierTest(unittest.TestCase):
    def test_apply_marks_estimated_values_when_fee_calculation_incomplete(self):
        metrics = PositionMetricsWarningApplier().apply({
            'fee_calculation_complete': False,
            'principal_calculation_complete': False,
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
                'fee_calculation_complete': True,
                'principal_calculation_complete': True,
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
        self.assertFalse(metrics['fee_calculation_complete'])
        self.assertFalse(metrics['principal_calculation_complete'])
        self.assertEqual(metrics['value_warning_codes'], ['estimated_values'])
        self.assertIn('incomplete history', metrics['value_warning_message'])


if __name__ == '__main__':
    unittest.main()
