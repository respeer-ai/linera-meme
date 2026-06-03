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
        self.assertIn('CREATE TABLE IF NOT EXISTS claim_balance_diagnostics', sql)
        self.assertIn('derivation_source VARCHAR(64) NOT NULL', sql)
        self.assertIn('derivation_confidence VARCHAR(32) NOT NULL', sql)
        self.assertIn('execution_chain_id VARCHAR(64) NOT NULL', sql)
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


if __name__ == '__main__':
    unittest.main()
