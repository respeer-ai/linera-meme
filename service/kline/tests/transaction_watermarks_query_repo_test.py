import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.transaction_watermarks_query_repo import TransactionWatermarksQueryRepository  # noqa: E402


class TransactionWatermarksQueryRepositoryTest(unittest.TestCase):
    class FakeProgrammingError(Exception):
        def __init__(self, errno, message):
            super().__init__(message)
            self.errno = errno

    class FakeCursor:
        def __init__(self, rows, error=None):
            self.rows = rows
            self.error = error
            self.executed = []

        def execute(self, sql, params=()):
            self.executed.append((' '.join(sql.split()), params))
            if self.error is not None:
                raise self.error

        def fetchall(self):
            return list(self.rows)

    class FakeDb:
        def __init__(self, rows, error=None):
            self.cursor_dict = TransactionWatermarksQueryRepositoryTest.FakeCursor(rows, error=error)
            self.ensure_count = 0

        def ensure_fresh_read_connection(self):
            self.ensure_count += 1

    def test_reads_latest_watermarks_from_settled_trades(self):
        db = self.FakeDb([
            {
                'pool_id': 1001,
                'pool_application': 'chain-a:pool-app',
                'created_at': 5000,
                'transaction_id': 12,
                'token_reversed': 0,
            },
            {
                'pool_id': 1001,
                'pool_application': 'chain-a:pool-app',
                'created_at': 5000,
                'transaction_id': 11,
                'token_reversed': 1,
            },
            {
                'pool_id': 1002,
                'pool_application': 'chain-b:pool-app-2',
                'created_at': 7000,
                'transaction_id': 20,
                'token_reversed': 1,
            },
        ])
        repository = TransactionWatermarksQueryRepository(db)

        watermarks = repository.get_latest_transaction_watermarks()

        self.assertEqual(db.ensure_count, 1)
        self.assertIn('FROM settled_trades st', db.cursor_dict.executed[0][0])
        self.assertEqual(
            watermarks,
            {
                (1001, 'chain-a', 'pool-app'): (5000, 12, 0),
                (1002, 'chain-b', 'pool-app-2'): (7000, 20, 1),
            },
        )

    def test_returns_empty_when_settled_trades_table_is_missing(self):
        db = self.FakeDb(
            [],
            error=self.FakeProgrammingError(
                1146,
                "1146 (42S02): Table 'linera_swap_kline.settled_trades' doesn't exist",
            ),
        )
        repository = TransactionWatermarksQueryRepository(db)

        watermarks = repository.get_latest_transaction_watermarks()

        self.assertEqual(db.ensure_count, 1)
        self.assertEqual(watermarks, {})
