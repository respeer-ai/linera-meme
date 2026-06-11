import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from position_metrics_value_support import PositionMetricsValueSupport
from market.position_metrics_snapshot_builder import PositionMetricsSnapshotBuilder


class ApplyPositionStateTest(unittest.TestCase):
    ATTOS_SCALE = 10 ** 18

    def _attos(self, value):
        return int(value * self.ATTOS_SCALE)

    def setUp(self):
        from decimal import Decimal
        value_support = PositionMetricsValueSupport(
            attos_scale=self.ATTOS_SCALE,
            display_quantum=Decimal('0.000000000000000001'),
            epsilon=Decimal('0.000000000001'),
            liquidity_mint_tolerance_attos=100,
            swap_out_tolerance_attos=1,
        )
        self.builder = PositionMetricsSnapshotBuilder(
            snapshot_materialization_inputs_repository=None,
            attos_scale=self.ATTOS_SCALE,
        )
        self.builder.value_support = value_support

    def test_first_add_creates_position(self):
        state = {
            'running_liquidity': 0,
            'added_liquidity': 0,
            'removed_liquidity': 0,
            'current_liquidity': 0,
            'status': None,
            'current_round_liquidity_event_count': 0,
            'current_round_started_at': None,
            'current_round_started_transaction_id': None,
        }
        output = {
            'settled_output_type': 'settled_liquidity_change',
            'transaction_type': 'AddLiquidity',
            'liquidity': '10',
            'amount_0_in': '100', 'amount_0_out': '0',
            'amount_1_in': '100', 'amount_1_out': '0',
            'created_at': 1000, 'transaction_id': 1,
        }
        result = self.builder.apply_position_state(state, output)

        self.assertEqual(result['running_liquidity'], self._attos(10))
        self.assertEqual(result['current_liquidity'], self._attos(10))
        self.assertEqual(result['status'], 'active')
        self.assertEqual(result['basis_type'], 'add_liquidity')
        self.assertEqual(result['basis_amount_0'], '100')
        self.assertEqual(result['basis_amount_1'], '100')
        self.assertEqual(result['basis_time_ms'], 1000)
        self.assertEqual(result['basis_transaction_id'], 1)
        self.assertEqual(result['added_liquidity'], self._attos(10))
        self.assertEqual(result['removed_liquidity'], 0)
        self.assertEqual(result['current_round_liquidity_event_count'], 1)
        self.assertEqual(result['current_round_started_at'], 1000)
        self.assertEqual(result['current_round_started_transaction_id'], 1)

    def test_remove_closes_position(self):
        state = {
            'running_liquidity': self._attos(10),
            'added_liquidity': self._attos(10),
            'removed_liquidity': 0,
            'current_liquidity': self._attos(10),
            'status': 'active',
            'current_round_liquidity_event_count': 1,
            'current_round_started_at': 1000,
            'current_round_started_transaction_id': 1,
        }
        output = {
            'settled_output_type': 'settled_liquidity_change',
            'transaction_type': 'RemoveLiquidity',
            'liquidity': '10',
            'amount_0_in': '0', 'amount_0_out': '100',
            'amount_1_in': '0', 'amount_1_out': '100',
            'created_at': 2000, 'transaction_id': 2,
        }
        result = self.builder.apply_position_state(state, output)

        self.assertEqual(result['running_liquidity'], 0)
        self.assertEqual(result['current_liquidity'], 0)
        self.assertEqual(result['status'], 'closed')
        self.assertEqual(result['basis_type'], 'remove_liquidity')
        self.assertEqual(result['removed_liquidity'], self._attos(10))
        self.assertEqual(result['basis_time_ms'], 2000)

    def test_partial_remove_keeps_active(self):
        state = {
            'running_liquidity': self._attos(10),
            'added_liquidity': self._attos(10),
            'removed_liquidity': 0,
            'current_liquidity': self._attos(10),
            'status': 'active',
            'current_round_liquidity_event_count': 1,
            'current_round_started_at': 1000,
            'current_round_started_transaction_id': 1,
        }
        output = {
            'settled_output_type': 'settled_liquidity_change',
            'transaction_type': 'RemoveLiquidity',
            'liquidity': '3',
            'amount_0_in': '0', 'amount_0_out': '30',
            'amount_1_in': '0', 'amount_1_out': '30',
            'created_at': 2000, 'transaction_id': 2,
        }
        result = self.builder.apply_position_state(state, output)

        self.assertEqual(result['running_liquidity'], self._attos(7))
        self.assertEqual(result['current_liquidity'], self._attos(7))
        self.assertEqual(result['status'], 'active')

    def test_multi_round(self):
        state = {
            'running_liquidity': 0,
            'added_liquidity': 0, 'removed_liquidity': 0,
            'current_liquidity': 0, 'status': 'closed',
            'current_round_liquidity_event_count': 0,
            'current_round_started_at': None,
            'current_round_started_transaction_id': None,
        }
        add1 = {
            'settled_output_type': 'settled_liquidity_change',
            'transaction_type': 'AddLiquidity',
            'liquidity': '10',
            'amount_0_in': '100', 'amount_0_out': '0',
            'amount_1_in': '100', 'amount_1_out': '0',
            'created_at': 1000, 'transaction_id': 1,
        }
        result = self.builder.apply_position_state(state, add1)
        self.assertEqual(result['current_round_liquidity_event_count'], 1)
        self.assertEqual(result['current_round_started_at'], 1000)

        rem = {
            'settled_output_type': 'settled_liquidity_change',
            'transaction_type': 'RemoveLiquidity',
            'liquidity': '10',
            'amount_0_in': '0', 'amount_0_out': '100',
            'amount_1_in': '0', 'amount_1_out': '100',
            'created_at': 2000, 'transaction_id': 2,
        }
        result = self.builder.apply_position_state(result, rem)
        self.assertEqual(result['running_liquidity'], 0)
        self.assertEqual(result['status'], 'closed')

        add2 = {
            'settled_output_type': 'settled_liquidity_change',
            'transaction_type': 'AddLiquidity',
            'liquidity': '5',
            'amount_0_in': '50', 'amount_0_out': '0',
            'amount_1_in': '50', 'amount_1_out': '0',
            'created_at': 3000, 'transaction_id': 3,
        }
        result = self.builder.apply_position_state(result, add2)
        self.assertEqual(result['running_liquidity'], self._attos(5))
        self.assertEqual(result['status'], 'active')
        self.assertEqual(result['current_round_liquidity_event_count'], 1)
        self.assertEqual(result['current_round_started_at'], 3000)
        self.assertEqual(result['current_round_started_transaction_id'], 3)
