import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.position_state_projection_repo import PositionStateProjectionRepository  # noqa: E402


class FakeCursor:
    def __init__(self):
        self.executed = []
        self.fetchone_result = {'position_state_id': 'pos-1'}

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


class PositionStateProjectionRepositoryTest(unittest.TestCase):
    def test_get_position_basis_snapshot_reads_position_state_table(self):
        db = FakeDb()
        repository = PositionStateProjectionRepository(db)

        row = repository.get_position_basis_snapshot(
            owner='chain:owner-a',
            pool_application_id='pool-app',
        )

        self.assertEqual(row, {'position_state_id': 'pos-1'})
        self.assertEqual(db.ensure_fresh_read_connection_called, 1)
        executed_sql, params = db.cursor_dict.executed[0]
        self.assertIn('FROM position_state_v2', executed_sql)
        self.assertEqual(params, ('chain:owner-a', 'pool-app', 'active'))


if __name__ == '__main__':
    unittest.main()
