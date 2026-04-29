import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.position_state_snapshot_repo import PositionStateSnapshotRepository  # noqa: E402


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.executed = []
        self.closed = False
        self.fetchone_result = None

    def execute(self, sql: str, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.fetchone_result

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instances = []
        self.commit_count = 0
        self.fetchone_result = None

    def cursor(self, **_kwargs):
        cursor = FakeCursor(self)
        cursor.fetchone_result = self.fetchone_result
        self.cursor_instances.append(cursor)
        return cursor

    def commit(self):
        self.commit_count += 1


class PositionStateSnapshotRepositoryTest(unittest.TestCase):
    def test_ensure_schema_creates_position_state_table(self):
        connection = FakeConnection()
        repository = PositionStateSnapshotRepository(connection)

        repository.ensure_schema()

        executed_sql = connection.cursor_instances[0].executed[0][0]
        self.assertIn('CREATE TABLE IF NOT EXISTS position_state_v2', executed_sql)
        self.assertEqual(connection.commit_count, 1)

    def test_upsert_position_states_persists_canonical_payload_json(self):
        connection = FakeConnection()
        repository = PositionStateSnapshotRepository(connection)

        count = repository.upsert_position_states(
            [
                {
                    'position_state_id': 'pos-1',
                    'owner': 'chain:owner-a',
                    'pool_application_id': 'pool-app',
                    'pool_chain_id': 'pool-chain',
                    'status': 'active',
                    'basis_type': 'add_liquidity',
                    'current_liquidity': '10',
                    'basis_liquidity': '7',
                    'basis_amount_0': '11',
                    'basis_amount_1': '12',
                    'basis_time_ms': 1234,
                    'basis_transaction_id': 9,
                    'source_event_key': 'evt-1',
                    'state_payload_json': {'basis': {'tx': 9}},
                }
            ]
        )

        self.assertEqual(count, 1)
        executed_sql, params = connection.cursor_instances[0].executed[0]
        self.assertIn('INSERT INTO position_state_v2', executed_sql)
        self.assertEqual(params[13], '{"basis":{"tx":9}}')
        self.assertEqual(connection.commit_count, 1)

    def test_get_position_state_reads_by_owner_pool_and_status(self):
        connection = FakeConnection()
        connection.fetchone_result = {'position_state_id': 'pos-1'}
        repository = PositionStateSnapshotRepository(connection)

        row = repository.get_position_state(
            owner='chain:owner-a',
            pool_application_id='pool-app',
            status='active',
        )

        self.assertEqual(row, {'position_state_id': 'pos-1'})
        executed_sql, params = connection.cursor_instances[0].executed[0]
        self.assertIn('FROM position_state_v2', executed_sql)
        self.assertEqual(params, ('chain:owner-a', 'pool-app', 'active'))

    def test_replace_position_states_deletes_previous_rows_before_upsert(self):
        connection = FakeConnection()
        repository = PositionStateSnapshotRepository(connection)

        count = repository.replace_position_states(
            owner='chain:owner-a',
            pool_application_id='pool-app',
            states=[
                {
                    'position_state_id': 'pos-closed',
                    'owner': 'chain:owner-a',
                    'pool_application_id': 'pool-app',
                    'pool_chain_id': 'pool-chain',
                    'status': 'closed',
                    'basis_type': 'remove_liquidity',
                    'current_liquidity': '0',
                    'basis_liquidity': '0',
                    'basis_amount_0': '3',
                    'basis_amount_1': '4',
                    'basis_time_ms': 2234,
                    'basis_transaction_id': 10,
                    'source_event_key': 'evt-closed',
                    'state_payload_json': {'basis': {'tx': 10}},
                }
            ],
        )

        self.assertEqual(count, 1)
        delete_sql, delete_params = connection.cursor_instances[0].executed[0]
        insert_sql, _insert_params = connection.cursor_instances[0].executed[1]
        self.assertIn('DELETE FROM position_state_v2', delete_sql)
        self.assertEqual(delete_params, ('chain:owner-a', 'pool-app'))
        self.assertIn('INSERT INTO position_state_v2', insert_sql)
        self.assertEqual(connection.commit_count, 1)


if __name__ == '__main__':
    unittest.main()
