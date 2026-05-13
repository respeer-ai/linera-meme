import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.position_metrics_snapshot_principal_simulator import PositionMetricsSnapshotPrincipalSimulator  # noqa: E402


class PositionMetricsSnapshotPrincipalSimulatorTest(unittest.TestCase):
    def _simulator(self):
        return PositionMetricsSnapshotPrincipalSimulator(
            to_attos=lambda value: None if value is None else int(value),
            from_attos=lambda value: value,
            serialize_attos=lambda value: str(value),
            swap_expected_out_attos=lambda tx_type, reserve0, reserve1, amount0_in, amount1_in: (
                amount1_in * reserve0 // (reserve1 + amount1_in)
                if tx_type == 'BuyToken0'
                else amount0_in * reserve1 // (reserve0 + amount0_in)
            ),
            effective_total_supply_attos=lambda state: int(state.get('total_supply_after') or 0),
        )

    def test_simulate_current_principal_supports_adds_after_intervening_swaps(self):
        result = self._simulator().simulate_current_principal(
            effective_history=[
                {'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 11, 'created_at': 1100, 'transaction_type': 'BuyToken0', 'amount_1_in': 10},
                {'transaction_id': 12, 'created_at': 1200, 'transaction_type': 'AddLiquidity', 'amount_0_in': 5, 'amount_1_in': 20},
            ],
            states=[
                {'reserve0_after': 10, 'reserve1_after': 10, 'total_supply_after': 10},
                {'reserve0_after': 6, 'reserve1_after': 20, 'total_supply_after': 10},
                {'reserve0_after': 11, 'reserve1_after': 40, 'total_supply_after': 20},
            ],
            latest_position_tx={'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
            tracked_liquidity_attos=10,
            basis_type='add_liquidity',
            basis_opens_current_round=True,
            current_round_trade_count_before_basis=0,
        )

        self.assertEqual(
            result,
            {
                'principal_amount_0_current': '5',
                'principal_amount_1_current': '20',
                'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                'post_basis_add_count': 1,
                'post_basis_remove_count': 0,
                'post_basis_swap_count': 1,
                'basis_protocol_fee_liquidity_minted': '0',
                'post_basis_protocol_fee_liquidity_minted': '0',
                'post_basis_protocol_fee_mint_event_count': 0,
                'post_basis_protocol_fee_liquidity_minted_before_first_add': '0',
                'fee_to_continuous_protocol_fee_liquidity_current': '0',
                'protocol_fee_liquidity_provenance_case': 'no_protocol_fee_mints',
            },
        )

    def test_simulate_current_principal_supports_remove_after_basis(self):
        result = self._simulator().simulate_current_principal(
            effective_history=[
                {'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'RemoveLiquidity'},
                {'transaction_id': 11, 'created_at': 1100, 'transaction_type': 'BuyToken0', 'amount_1_in': 100},
                {'transaction_id': 12, 'created_at': 1200, 'transaction_type': 'RemoveLiquidity', 'liquidity': 10},
            ],
            states=[
                {'reserve0_after': 100, 'reserve1_after': 100, 'total_supply_after': 100},
                {'reserve0_after': 50, 'reserve1_after': 200, 'total_supply_after': 100},
                {'reserve0_after': 45, 'reserve1_after': 180, 'total_supply_after': 90},
            ],
            latest_position_tx={'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'RemoveLiquidity'},
            tracked_liquidity_attos=50,
            basis_type='remove_liquidity',
            basis_opens_current_round=False,
            current_round_trade_count_before_basis=1,
        )

        self.assertEqual(
            result,
            {
                'principal_amount_0_current': '25',
                'principal_amount_1_current': '100',
                'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                'post_basis_add_count': 0,
                'post_basis_remove_count': 1,
                'post_basis_swap_count': 1,
                'basis_protocol_fee_liquidity_minted': '0',
                'post_basis_protocol_fee_liquidity_minted': '0',
                'post_basis_protocol_fee_mint_event_count': 0,
                'post_basis_protocol_fee_liquidity_minted_before_first_add': '0',
                'fee_to_continuous_protocol_fee_liquidity_current': '0',
                'protocol_fee_liquidity_provenance_case': 'no_protocol_fee_mints',
            },
        )

    def test_simulate_current_principal_records_protocol_fee_liquidity_provenance(self):
        result = self._simulator().simulate_current_principal(
            effective_history=[
                {'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 11, 'created_at': 1100, 'transaction_type': 'BuyToken0', 'amount_1_in': 100},
                {'transaction_id': 12, 'created_at': 1200, 'transaction_type': 'AddLiquidity', 'amount_0_in': 20, 'amount_1_in': 40},
                {'transaction_id': 13, 'created_at': 1300, 'transaction_type': 'RemoveLiquidity', 'liquidity': 10},
            ],
            states=[
                {
                    'reserve0_after': 100,
                    'reserve1_after': 100,
                    'total_supply_after': 100,
                    'protocol_fee_minted_after': 5,
                },
                {
                    'reserve0_after': 50,
                    'reserve1_after': 200,
                    'total_supply_after': 100,
                    'protocol_fee_minted_after': 0,
                },
                {
                    'reserve0_after': 70,
                    'reserve1_after': 240,
                    'total_supply_after': 120,
                    'protocol_fee_minted_after': 7,
                },
                {
                    'reserve0_after': 64,
                    'reserve1_after': 220,
                    'total_supply_after': 117,
                    'protocol_fee_minted_after': 3,
                },
            ],
            latest_position_tx={'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
            tracked_liquidity_attos=100,
            basis_type='add_liquidity',
            basis_opens_current_round=True,
            current_round_trade_count_before_basis=0,
        )

        self.assertEqual(result['basis_protocol_fee_liquidity_minted'], '5')
        self.assertEqual(result['post_basis_protocol_fee_liquidity_minted'], '10')
        self.assertEqual(result['post_basis_protocol_fee_mint_event_count'], 2)
        self.assertEqual(result['post_basis_protocol_fee_liquidity_minted_before_first_add'], '7')
        self.assertEqual(result['fee_to_continuous_protocol_fee_liquidity_current'], '15')
        self.assertEqual(result['protocol_fee_liquidity_provenance_case'], 'basis_and_post_basis_mints')


if __name__ == '__main__':
    unittest.main()
