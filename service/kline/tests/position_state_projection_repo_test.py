import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.position_state_projection_repo import PositionStateProjectionRepository  # noqa: E402


class FakeDb:
    def __init__(self, row):
        self.row = row
        self.ensure_fresh_read_connection_calls = 0
        self.cursor_dict = self
        self.executed = []

    def ensure_fresh_read_connection(self):
        self.ensure_fresh_read_connection_calls += 1

    def fresh_cursor(self, dictionary=False):
        self.ensure_fresh_read_connection()
        return self.cursor_dict

    def execute(self, sql, params):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.row

    def close(self):
        return None


class PositionStateProjectionRepositoryTest(unittest.TestCase):
    def test_get_position_basis_snapshot_projects_semantic_facts(self):
        db = FakeDb(
            {
                'position_state_id': 'pos-1',
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 11,
                'basis_time_ms': 1234,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                    'current_round_trade_count_before_basis': 0,
                    'exact_current_principal': {
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'protocol_fee_current_owner_provenance_case': 'owner_only',
                    },
                    'fee_to_continuity': {
                        'continuity_case': 'continuous_no_changes_after_basis',
                        'known_before_basis': True,
                    },
                },
            }
        )
        repository = PositionStateProjectionRepository(db)

        snapshot = repository.get_position_basis_snapshot(
            owner='chain:owner-a',
            pool_application_id='pool-app',
            status='active',
        )

        self.assertEqual(db.ensure_fresh_read_connection_calls, 1)
        self.assertEqual(db.executed[0][1], ('chain:owner-a', 'pool-app', 'active'))
        self.assertEqual(
            snapshot['semantic_facts'],
            {
                'prior_liquidity_before_basis': '0',
                'has_only_zero_liquidity_before_basis': None,
                'basis_opens_current_round': True,
                'current_round_liquidity_event_count': None,
                'current_round_started_at': None,
                'current_round_started_transaction_id': None,
                'current_round_trade_count_before_basis': 0,
                'trade_count_between_basis_and_fee_free_basis': None,
                'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                'principal_amount_0_current': None,
                'principal_amount_1_current': None,
                'post_basis_remove_count': None,
                'basis_protocol_fee_liquidity_minted': None,
                'post_basis_protocol_fee_liquidity_minted': None,
                'post_basis_protocol_fee_mint_event_count': None,
                'post_basis_protocol_fee_liquidity_minted_before_first_add': None,
                'fee_to_continuous_protocol_fee_liquidity_current': None,
                'protocol_fee_liquidity_provenance_case': None,
                'protocol_fee_current_owner_provenance_case': 'owner_only',
                'basis_protocol_fee_liquidity_owned_by_current_owner': None,
                'post_basis_protocol_fee_liquidity_owned_by_current_owner': None,
                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': None,
                'protocol_fee_liquidity_owned_by_current_owner_current': None,
                'protocol_fee_liquidity_owned_by_other_accounts': None,
                'protocol_fee_liquidity_owner_unknown': None,
                'full_protocol_fee_liquidity_owned_by_current_owner': None,
                'full_protocol_fee_liquidity_owned_by_other_accounts': None,
                'full_protocol_fee_liquidity_owner_unknown': None,
                'full_protocol_fee_current_owner_provenance_case': None,
                'fee_to_continuity_case': 'continuous_no_changes_after_basis',
                'fee_to_continuity_change_count_after_basis': None,
                'fee_to_continuity_known_before_basis': True,
                'fee_to_continuity_owner': None,
                'fee_to_account_at_basis': None,
                'fee_to_account_latest_known': None,
                'trailing_24h_fee_amount_0': None,
                'trailing_24h_fee_amount_1': None,
                'trailing_24h_fee_window_start_ms': None,
                'trailing_24h_fee_window_end_ms': None,
            },
        )


if __name__ == '__main__':
    unittest.main()
