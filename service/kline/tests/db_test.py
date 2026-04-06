import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


class FakeCursor:
    def __init__(self, database_catalog, table_catalog, index_catalog):
        self.database_catalog = database_catalog
        self.table_catalog = table_catalog
        self.index_catalog = index_catalog
        self.dictionary = False
        self.executed = []
        self._last_result = []

    def execute(self, query, params=None):
        normalized = ' '.join(query.split())
        self.executed.append((normalized, params))

        if normalized == 'SHOW DATABASES':
          self._last_result = [(name,) for name in self.database_catalog]
          return

        if normalized == 'SHOW TABLES':
          self._last_result = [(name,) for name in self.table_catalog]
          return

        if normalized.startswith('SHOW INDEX FROM transactions'):
          self._last_result = self.index_catalog
          return

        self._last_result = []

    def fetchall(self):
        return list(self._last_result)

    def close(self):
        return None


class FakeConnection:
    def __init__(self, database_catalog, table_catalog, index_catalog):
        self.database_catalog = database_catalog
        self.table_catalog = table_catalog
        self.index_catalog = index_catalog
        self.commits = 0
        self.closed = False
        self.cursors = []

    def cursor(self, dictionary=False):
        cursor = FakeCursor(self.database_catalog, self.table_catalog, self.index_catalog)
        cursor.dictionary = dictionary
        self.cursors.append(cursor)
        return cursor

    def commit(self):
        self.commits += 1

    def close(self):
        self.closed = True


swap_stub = types.ModuleType('swap')
swap_stub.Transaction = object
swap_stub.Pool = object
sys.modules.setdefault('swap', swap_stub)

mysql_stub = types.ModuleType('mysql')
mysql_connector_stub = types.ModuleType('mysql.connector')
mysql_connector_stub.connect = None
mysql_stub.connector = mysql_connector_stub
sys.modules.setdefault('mysql', mysql_stub)
sys.modules.setdefault('mysql.connector', mysql_connector_stub)

pandas_stub = types.ModuleType('pandas')
numpy_stub = types.ModuleType('numpy')
sys.modules.setdefault('pandas', pandas_stub)
sys.modules.setdefault('numpy', numpy_stub)

from db import Db, align_timestamp_to_minute_ms, build_kline_points_query  # noqa: E402


class DbIndexInitializationTest(unittest.TestCase):
    def setUp(self):
        self.database_catalog = ['kline']
        self.table_catalog = ['pools', 'transactions']
        self.index_catalog = [
            ('transactions', 0, 'PRIMARY', 1, 'pool_id'),
            ('transactions', 0, 'PRIMARY', 2, 'transaction_id'),
            ('transactions', 0, 'PRIMARY', 3, 'token_reversed'),
        ]
        self.connections = []

    def create_connection(self, **_kwargs):
        connection = FakeConnection(
            self.database_catalog,
            self.table_catalog,
            self.index_catalog,
        )
        self.connections.append(connection)
        return connection

    @patch('db.mysql.connector.connect')
    def test_creates_range_query_index_when_missing(self, connect_mock):
        connect_mock.side_effect = self.create_connection

        Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        runtime_connection = self.connections[-1]
        executed_queries = [query for cursor in runtime_connection.cursors for query, _ in cursor.executed]

        self.assertTrue(any(
            'CREATE INDEX idx_transactions_pool_reverse_created_at ON transactions (pool_id, token_reversed, created_at)'
            in query for query in executed_queries
        ))

    @patch('db.mysql.connector.connect')
    def test_does_not_recreate_range_query_index_when_present(self, connect_mock):
        self.index_catalog.append(
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 1, 'pool_id'),
        )
        connect_mock.side_effect = self.create_connection

        Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        runtime_connection = self.connections[-1]
        executed_queries = [query for cursor in runtime_connection.cursors for query, _ in cursor.executed]

        self.assertFalse(any(
            'CREATE INDEX idx_transactions_pool_reverse_created_at ON transactions (pool_id, token_reversed, created_at)'
            in query for query in executed_queries
        ))


if __name__ == '__main__':
    unittest.main()


class DbQueryHelperTest(unittest.TestCase):
    def test_align_timestamp_to_minute_ms_preserves_millisecond_semantics(self):
        self.assertEqual(
            align_timestamp_to_minute_ms(1_710_000_060_999),
            1_710_000_060_000,
        )

    def test_build_kline_points_query_orders_by_created_at_for_indexed_scan(self):
        query = build_kline_points_query(
            table_name='transactions',
            pool_id=7,
            token_reversed=True,
            start_at=1_000_000,
            end_at=2_000_000,
        )

        self.assertIn('WHERE pool_id = 7', query)
        self.assertIn('AND token_reversed = True', query)
        self.assertIn('AND created_at >= 1000000', query)
        self.assertIn('AND created_at <= 2000000', query)
        self.assertIn('ORDER BY created_at ASC', query)
