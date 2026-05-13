import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.position_metrics_protocol_fee_ownership_tracker import PositionMetricsProtocolFeeOwnershipTracker  # noqa: E402


class PositionMetricsProtocolFeeOwnershipTrackerTest(unittest.TestCase):
    def _tracker(self):
        return PositionMetricsProtocolFeeOwnershipTracker(
            serialize_attos=lambda value: str(value),
        )

    def test_summarize_marks_all_protocol_fee_mints_owned_by_current_owner(self):
        result = self._tracker().summarize(
            owner='chain-fee:0xfee-owner',
            effective_history=[
                {'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 11, 'created_at': 1100, 'transaction_type': 'BuyToken0'},
                {'transaction_id': 12, 'created_at': 1200, 'transaction_type': 'RemoveLiquidity'},
            ],
            states=[
                {'protocol_fee_minted_after': 2},
                {'protocol_fee_minted_after': 0},
                {'protocol_fee_minted_after': 3},
            ],
            latest_position_tx={
                'transaction_id': 10,
                'created_at': 1000,
                'transaction_type': 'AddLiquidity',
            },
            fee_to_history=[
                {'transaction_id': 9, 'created_at': 900, 'fee_to_account': 'chain-fee:0xfee-owner'},
                {'transaction_id': 13, 'created_at': 1300, 'fee_to_account': 'chain-fee:0xother-owner'},
            ],
        )

        self.assertEqual(result['basis_protocol_fee_liquidity_owned_by_current_owner'], '2')
        self.assertEqual(result['post_basis_protocol_fee_liquidity_owned_by_current_owner'], '3')
        self.assertEqual(result['post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add'], '3')
        self.assertEqual(result['protocol_fee_liquidity_owned_by_current_owner_current'], '5')
        self.assertEqual(result['protocol_fee_liquidity_owned_by_other_accounts'], '0')
        self.assertEqual(result['protocol_fee_liquidity_owner_unknown'], '0')
        self.assertEqual(result['protocol_fee_current_owner_provenance_case'], 'all_mints_owned_by_current_owner')

    def test_summarize_marks_mixed_owner_protocol_fee_mints(self):
        result = self._tracker().summarize(
            owner='chain-fee:0xfee-owner',
            effective_history=[
                {'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 11, 'created_at': 1100, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 12, 'created_at': 1200, 'transaction_type': 'RemoveLiquidity'},
            ],
            states=[
                {'protocol_fee_minted_after': 2},
                {'protocol_fee_minted_after': 4},
                {'protocol_fee_minted_after': 3},
            ],
            latest_position_tx={
                'transaction_id': 10,
                'created_at': 1000,
                'transaction_type': 'AddLiquidity',
            },
            fee_to_history=[
                {'transaction_id': 9, 'created_at': 900, 'fee_to_account': 'chain-fee:0xfee-owner'},
                {'transaction_id': 11, 'created_at': 1100, 'fee_to_account': 'chain-fee:0xother-owner'},
            ],
        )

        self.assertEqual(result['protocol_fee_liquidity_owned_by_current_owner_current'], '2')
        self.assertEqual(result['protocol_fee_liquidity_owned_by_other_accounts'], '7')
        self.assertEqual(result['protocol_fee_liquidity_owner_unknown'], '0')
        self.assertEqual(result['protocol_fee_current_owner_provenance_case'], 'owner_and_non_owner_mints')


if __name__ == '__main__':
    unittest.main()
