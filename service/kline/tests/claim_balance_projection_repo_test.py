import sys
import unittest
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[1] / 'src'
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from storage.mysql.claim_balance_projection_repo import ClaimBalanceProjectionRepository  # noqa: E402


class ClaimBalanceProjectionRepositoryTest(unittest.TestCase):
    class FakeCursor:
        def __init__(self):
            self.executed = []
            self.rows = []
            self.rowcount = 0

        def execute(self, sql, params=None):
            self.executed.append((sql, params))

        def fetchall(self):
            return list(self.rows)

        def close(self):
            pass

    class FakeConnection:
        def __init__(self):
            self.cursor_obj = ClaimBalanceProjectionRepositoryTest.FakeCursor()
            self.commit_count = 0

        def cursor(self, dictionary=False):
            return self.cursor_obj

        def commit(self):
            self.commit_count += 1

    def test_ensure_schema_creates_delta_and_diagnostic_tables(self):
        connection = self.FakeConnection()
        repository = ClaimBalanceProjectionRepository(connection)

        repository.ensure_schema()

        sql = '\n'.join(statement for statement, _ in connection.cursor_obj.executed)
        self.assertIn('CREATE TABLE IF NOT EXISTS claim_balance_deltas', sql)
        self.assertIn('claim_balance_delta_id VARCHAR(512) NOT NULL', sql)
        self.assertIn('MODIFY COLUMN claim_balance_delta_id VARCHAR(512) NOT NULL', sql)
        self.assertIn('CREATE TABLE IF NOT EXISTS claim_balance_diagnostics', sql)
        self.assertIn('derivation_source VARCHAR(64) NOT NULL', sql)
        self.assertIn('derivation_confidence VARCHAR(32) NOT NULL', sql)
        self.assertIn('execution_chain_id VARCHAR(64) NOT NULL', sql)
        self.assertIn('KEY idx_claim_balance_delta_owner (owner(128), pool_application_id(128), execution_chain_id, token(128))', sql)
        self.assertIn('KEY idx_claim_balance_diagnostic_pool (pool_application_id(128), execution_chain_id)', sql)
        self.assertEqual(connection.commit_count, 1)

    def test_upsert_claim_balance_deltas_preserves_derivation_fields(self):
        connection = self.FakeConnection()
        repository = ClaimBalanceProjectionRepository(connection)

        count = repository.upsert_claim_balance_deltas([
            {
                'claim_balance_delta_id': 'delta-1',
                'normalized_event_id': 'event-1',
                'pool_application_id': 'pool-app',
                'execution_chain_id': 'chain-pool',
                'token': 'token-app',
                'owner': 'owner-account',
                'balance_kind': 'claimable',
                'delta_amount': '13',
                'delta_direction': 'credit',
                'block_hash': 'block-1',
                'block_height': 7,
                'transaction_index': 2,
                'message_index': 3,
                'rejected': False,
                'derivation_source': 'claim_transfer_receipt',
                'derivation_confidence': 'exact',
                'source_event_key': 'source-1',
                'event_payload_json': {'message_type': 'claim_transfer_receipt'},
            }
        ])

        self.assertEqual(count, 1)
        _sql, params = connection.cursor_obj.executed[0]
        self.assertEqual(params[0], 'delta-1')
        self.assertEqual(params[3], 'chain-pool')
        self.assertEqual(params[14], 'claim_transfer_receipt')
        self.assertEqual(params[15], 'exact')
        self.assertIn('"message_type":"claim_transfer_receipt"', params[17])
        self.assertEqual(connection.commit_count, 1)

    def test_upsert_claim_balance_diagnostics_preserves_partial_reason(self):
        connection = self.FakeConnection()
        repository = ClaimBalanceProjectionRepository(connection)

        count = repository.upsert_claim_balance_diagnostics([
            {
                'claim_balance_diagnostic_id': 'diag-1',
                'normalized_event_id': 'event-1',
                'pool_application_id': 'pool-app',
                'execution_chain_id': 'chain-pool',
                'diagnostic_type': 'missing_new_transaction_correlation',
                'derivation_source': 'swap_message',
                'derivation_confidence': 'partial',
                'block_hash': 'block-1',
                'block_height': 7,
                'transaction_index': 2,
                'message_index': 3,
                'rejected': False,
                'source_event_key': 'source-1',
                'event_payload_json': {'message_type': 'swap'},
            }
        ])

        self.assertEqual(count, 1)
        _sql, params = connection.cursor_obj.executed[0]
        self.assertEqual(params[0], 'diag-1')
        self.assertEqual(params[4], 'missing_new_transaction_correlation')
        self.assertEqual(params[5], 'swap_message')
        self.assertEqual(params[6], 'partial')
        self.assertIn('"message_type":"swap"', params[13])
        self.assertEqual(connection.commit_count, 1)


    def test_delete_claim_balance_diagnostics_for_events_deletes_selected_types(self):
        connection = self.FakeConnection()
        connection.cursor_obj.rowcount = 2
        repository = ClaimBalanceProjectionRepository(connection)

        count = repository.delete_claim_balance_diagnostics_for_events(
            normalized_event_ids={'event-b', 'event-a'},
            diagnostic_types={'ambiguous_new_transaction_correlation', 'missing_pool_token_metadata'},
        )

        sql, params = connection.cursor_obj.executed[0]
        self.assertIn('DELETE FROM claim_balance_diagnostics', sql)
        self.assertIn('normalized_event_id IN (%s, %s)', sql)
        self.assertIn('diagnostic_type IN (%s, %s)', sql)
        self.assertEqual(
            params,
            (
                'event-a',
                'event-b',
                'ambiguous_new_transaction_correlation',
                'missing_pool_token_metadata',
            ),
        )
        self.assertEqual(count, 2)
        self.assertEqual(connection.commit_count, 1)


    def test_delete_correlated_claim_balance_deltas_for_events_only_deletes_correlated_sources(self):
        connection = self.FakeConnection()
        connection.cursor_obj.rowcount = 3
        repository = ClaimBalanceProjectionRepository(connection)

        count = repository.delete_correlated_claim_balance_deltas_for_events(
            normalized_event_ids={'event-b', 'event-a'},
        )

        sql, params = connection.cursor_obj.executed[0]
        self.assertIn('DELETE FROM claim_balance_deltas', sql)
        self.assertIn('normalized_event_id IN (%s, %s)', sql)
        self.assertIn("derivation_source LIKE 'correlated\\_%'", sql)
        self.assertEqual(params, ('event-a', 'event-b'))
        self.assertEqual(count, 3)
        self.assertEqual(connection.commit_count, 1)


    def test_get_claim_balances_aggregates_projection_deltas_as_display_amounts(self):
        connection = self.FakeConnection()
        connection.cursor_obj.rows = [{
            'pool_application_id': 'pool-app',
            'execution_chain_id': 'pool-chain',
            'token': 'native',
            'owner': 'owner-account',
            'claimable_amount': '7.5',
            'claiming_amount': '3.25',
            'latest_block_height': 11,
            'latest_transaction_index': 2,
            'latest_message_index': 1,
            'projection_status': 'complete',
            'incomplete_diagnostic_count': 0,
        }]
        repository = ClaimBalanceProjectionRepository(connection)

        rows = repository.get_claim_balances(owner='owner-account')

        sql, params = connection.cursor_obj.executed[0]
        self.assertIn('FROM claim_balance_deltas', sql)
        self.assertIn('CAST(deltas.delta_amount AS DECIMAL(65, 0))', sql)
        self.assertIn('GREATEST(COALESCE(SUM(CASE', sql)
        self.assertIn('/ 1000000000000000000 AS claimable_amount', sql)
        self.assertIn('/ 1000000000000000000 AS claiming_amount', sql)
        self.assertIn("OR projection_status = 'incomplete'", sql)
        self.assertIn('WHERE deltas.owner = %s', sql)
        self.assertIn('GROUP BY deltas.pool_application_id, deltas.execution_chain_id, deltas.token, deltas.owner', sql)
        self.assertEqual(params, ('owner-account',))
        self.assertEqual(rows[0]['claimable_amount'], '7.5')
        self.assertEqual(rows[0]['claiming_amount'], '3.25')
        self.assertEqual(rows[0]['projection_status'], 'complete')
        self.assertEqual(rows[0]['diagnostics'], {'incomplete_count': 0})

    def test_get_claim_balances_clamps_negative_claimable_projection(self):
        connection = self.FakeConnection()
        connection.cursor_obj.rows = [{
            'pool_application_id': 'pool-app',
            'execution_chain_id': 'pool-chain',
            'token': 'native',
            'owner': 'owner-account',
            'claimable_amount': '0',
            'claiming_amount': '0',
            'latest_block_height': 11,
            'latest_transaction_index': 2,
            'latest_message_index': 1,
            'projection_status': 'incomplete',
            'incomplete_diagnostic_count': 3,
        }]
        repository = ClaimBalanceProjectionRepository(connection)

        rows = repository.get_claim_balances(owner='owner-account')

        sql, _params = connection.cursor_obj.executed[0]
        self.assertIn('GREATEST(COALESCE(SUM(CASE', sql)
        self.assertEqual(rows[0]['claimable_amount'], '0')
        self.assertEqual(rows[0]['projection_status'], 'incomplete')
        self.assertEqual(rows[0]['diagnostics'], {'incomplete_count': 3})

    def test_get_claim_balances_marks_incomplete_projection(self):
        connection = self.FakeConnection()
        connection.cursor_obj.rows = [{
            'pool_application_id': 'pool-app',
            'execution_chain_id': 'pool-chain',
            'token': 'native',
            'owner': 'owner-account',
            'claimable_amount': '0',
            'claiming_amount': '0',
            'latest_block_height': 11,
            'latest_transaction_index': 2,
            'latest_message_index': 1,
            'projection_status': 'incomplete',
            'incomplete_diagnostic_count': 3,
        }]
        repository = ClaimBalanceProjectionRepository(connection)

        rows = repository.get_claim_balances(owner='owner-account')

        sql, _params = connection.cursor_obj.executed[0]
        self.assertIn('claim_delta_requires_new_transaction_correlation', sql)
        self.assertIn('ambiguous_new_transaction_correlation', sql)
        self.assertEqual(rows[0]['claimable_amount'], '0')
        self.assertEqual(rows[0]['projection_status'], 'incomplete')
        self.assertEqual(rows[0]['diagnostics'], {'incomplete_count': 3})


if __name__ == '__main__':
    unittest.main()
