import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from position_metrics_swap_math_support import PositionMetricsSwapMathSupport
from position_metrics_value_support import PositionMetricsValueSupport
from market.position_metrics_snapshot_builder import PositionMetricsSnapshotBuilder


class ApplyPoolStateTest(unittest.TestCase):
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
        self.swap_math = PositionMetricsSwapMathSupport(
            to_attos=value_support.to_attos,
            from_attos=value_support.from_attos,
            swap_fee_numerator=997,
            swap_fee_denominator=1000,
            swap_out_tolerance_attos=1,
        )
        self.builder = PositionMetricsSnapshotBuilder(
            snapshot_materialization_inputs_repository=None,
            attos_scale=self.ATTOS_SCALE,
        )
        self.builder.swap_math_support = self.swap_math
        self.builder.value_support = value_support

    def test_apply_trade(self):
        state = {
            'reserve0': self._attos(1000), 'reserve1': self._attos(1000),
            'total_supply': self._attos(1000), 'k_last': self._attos(1000),
            'pending_protocol_fee': 0, 'total_minted_protocol_fee': 0,
            'swap_count': 0, 'last_trade_time_ms': 0, 'last_transaction_id': 0,
        }
        output = {
            'settled_output_type': 'settled_trade',
            'transaction_type': 'BuyToken0',
            'amount_0_in': '0', 'amount_0_out': '9.872',
            'amount_1_in': '10', 'amount_1_out': '0',
            'trade_time_ms': 1000, 'transaction_id': 1,
        }
        result = self.builder.apply_pool_state(state, output)

        self.assertLess(result['reserve0'], self._attos(1000))
        self.assertGreater(result['reserve1'], self._attos(1000))
        self.assertEqual(result['k_last'], state['k_last'])
        self.assertEqual(result['total_supply'], state['total_supply'])
        self.assertEqual(result['total_minted_protocol_fee'], 0)
        self.assertEqual(result['swap_count'], 1)
        expected_pending = self.swap_math.mint_fee_attos(
            state['total_supply'], result['reserve0'], result['reserve1'], state['k_last'],
        )
        self.assertEqual(result['pending_protocol_fee'], expected_pending)
        self.assertEqual(result['last_trade_time_ms'], 1000)

    def test_apply_add_liquidity(self):
        state = {
            'reserve0': self._attos(1005), 'reserve1': self._attos(1010),
            'total_supply': self._attos(1000), 'k_last': self._attos(1000),
            'pending_protocol_fee': 50, 'total_minted_protocol_fee': 950,
            'swap_count': 3, 'last_transaction_id': 0,
        }
        output = {
            'settled_output_type': 'settled_liquidity_change',
            'transaction_type': 'AddLiquidity',
            'liquidity': '5',
            'amount_0_in': '5', 'amount_0_out': '0',
            'amount_1_in': '5', 'amount_1_out': '0',
            'created_at': 2000, 'transaction_id': 4,
        }
        result = self.builder.apply_pool_state(state, output)

        self.assertEqual(result['total_minted_protocol_fee'], 1000)
        self.assertEqual(result['pending_protocol_fee'], 0)
        self.assertEqual(result['total_supply'], self._attos(1000) + 50 + self._attos(5))
        self.assertEqual(result['reserve0'], self._attos(1010))
        self.assertEqual(result['reserve1'], self._attos(1015))
        expected_k = math.isqrt(result['reserve0'] * result['reserve1'])
        self.assertEqual(result['k_last'], expected_k)
        self.assertEqual(result['last_liquidity_event_time_ms'], 2000)

    def test_apply_virtual_initial(self):
        state = {
            'reserve0': 0, 'reserve1': 0,
            'total_supply': 0, 'k_last': 0,
            'pending_protocol_fee': 0, 'total_minted_protocol_fee': 0,
            'swap_count': 0, 'last_transaction_id': 0,
        }
        output = {
            'settled_output_type': 'settled_liquidity_change',
            'transaction_type': 'AddLiquidity',
            'liquidity': '0',
            'liquidity_semantics': 'virtual_initial_liquidity',
            'amount_0_in': '1000', 'amount_0_out': '0',
            'amount_1_in': '1000', 'amount_1_out': '0',
            'created_at': 0, 'transaction_id': 1,
        }
        result = self.builder.apply_pool_state(state, output)

        expected_supply = math.isqrt(self._attos(1000) * self._attos(1000))
        self.assertEqual(result['total_supply'], expected_supply)
        self.assertEqual(result['total_minted_protocol_fee'], 0)
        self.assertEqual(result['pending_protocol_fee'], 0)
        self.assertEqual(result['reserve0'], self._attos(1000))
        self.assertEqual(result['reserve1'], self._attos(1000))

    def test_apply_remove_liquidity(self):
        state = {
            'reserve0': self._attos(1010), 'reserve1': self._attos(1015),
            'total_supply': self._attos(1050), 'k_last': self._attos(1000),
            'pending_protocol_fee': 30, 'total_minted_protocol_fee': 1000,
            'swap_count': 3, 'last_transaction_id': 4,
        }
        output = {
            'settled_output_type': 'settled_liquidity_change',
            'transaction_type': 'RemoveLiquidity',
            'liquidity': '10',
            'amount_0_in': '0', 'amount_0_out': '10',
            'amount_1_in': '0', 'amount_1_out': '10',
            'created_at': 3000, 'transaction_id': 5,
        }
        result = self.builder.apply_pool_state(state, output)

        self.assertEqual(result['total_minted_protocol_fee'], 1030)
        self.assertEqual(result['pending_protocol_fee'], 0)
        self.assertEqual(result['total_supply'], self._attos(1050) + 30 - self._attos(10))
        self.assertEqual(result['reserve0'], self._attos(1000))
        self.assertEqual(result['reserve1'], self._attos(1005))
