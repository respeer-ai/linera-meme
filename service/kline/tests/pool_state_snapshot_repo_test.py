import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.pool_state_snapshot_repo import PoolStateSnapshotRepository  # noqa: E402


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


class PoolStateSnapshotRepositoryTest(unittest.TestCase):
    def test_ensure_schema_creates_pool_state_table(self):
        connection = FakeConnection()
        repository = PoolStateSnapshotRepository(connection)

        repository.ensure_schema()

        executed_sql = connection.cursor_instances[0].executed[0][0]
        self.assertIn('CREATE TABLE IF NOT EXISTS pool_state_v2', executed_sql)
        migration_sql = connection.cursor_instances[0].executed[2][0]
        self.assertIn("pool_application_id LIKE '%:%'", migration_sql)
        self.assertIn("CONCAT(SUBSTRING_INDEX(pool_application_id, ':', -1), '@', pool_chain_id)", migration_sql)
        self.assertEqual(connection.commit_count, 1)

    def test_upsert_pool_states_persists_canonical_payload_json(self):
        connection = FakeConnection()
        repository = PoolStateSnapshotRepository(connection)

        count = repository.upsert_pool_states(
            [
                {
                    'pool_state_id': 'pool-state-1',
                    'pool_application_id': 'pool-app',
                    'pool_chain_id': 'pool-chain',
                    'last_trade_time_ms': 1234,
                    'last_liquidity_event_time_ms': 1200,
                    'last_transaction_id': 9,
                    'swap_count': 17,
                    'live_reserve_0': '100',
                    'live_reserve_1': '200',
                    'live_total_supply': '300',
                    'live_k_last': '400',
                    'fee_free_reserve_0': '90',
                    'fee_free_reserve_1': '190',
                    'fee_free_total_supply': '280',
                    'source_event_key': 'evt-2',
                    'state_payload_json': {'pool': {'swap_count': 17}},
                }
            ]
        )

        self.assertEqual(count, 1)
        executed_sql, params = connection.cursor_instances[0].executed[0]
        self.assertIn('INSERT INTO pool_state_v2', executed_sql)
        self.assertIsNone(params[11])
        self.assertIsNone(params[12])
        self.assertEqual(params[17], '{"pool":{"swap_count":17}}')
        self.assertEqual(connection.commit_count, 1)

    def test_get_pool_state_reads_by_pool_application(self):
        connection = FakeConnection()
        connection.fetchone_result = {'pool_state_id': 'pool-state-1'}
        repository = PoolStateSnapshotRepository(connection)

        row = repository.get_pool_state(pool_application_id='pool-app')

        self.assertEqual(row, {'pool_state_id': 'pool-state-1'})
        executed_sql, params = connection.cursor_instances[0].executed[0]
        self.assertIn('FROM pool_state_v2', executed_sql)
        self.assertEqual(params, ('pool-app',))


if __name__ == '__main__':
    unittest.main()
