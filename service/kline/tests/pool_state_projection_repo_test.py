import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.pool_state_projection_repo import PoolStateProjectionRepository  # noqa: E402


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.fetchone_result = {'pool_state_id': 'pool-state-1'}

    def execute(self, sql: str, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return self.fetchone_result


class FakeDb:
    def __init__(self):
        self.ensure_fresh_read_connection_called = 0
        self.cursor_dict = FakeCursor()

    def ensure_fresh_read_connection(self):
        self.ensure_fresh_read_connection_called += 1


class PoolStateProjectionRepositoryTest(unittest.TestCase):
    def test_get_pool_state_snapshot_reads_pool_state_table(self):
        db = FakeDb()
        repository = PoolStateProjectionRepository(db)

        row = repository.get_pool_state_snapshot(pool_application_id='pool-app')

        self.assertEqual(row, {'pool_state_id': 'pool-state-1'})
        self.assertEqual(db.ensure_fresh_read_connection_called, 1)
        executed_sql, params = db.cursor_dict.executed[0]
        self.assertIn('FROM pool_state_v2', executed_sql)
        self.assertEqual(params, ('pool-app',))


if __name__ == '__main__':
    unittest.main()
