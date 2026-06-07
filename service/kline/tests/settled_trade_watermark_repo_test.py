import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.settled_trade_watermark_repo import SettledTradeWatermarkRepository  # noqa: E402


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.executed = []
        self.closed = False

    def execute(self, sql: str, params=None):
        self.executed.append((sql, params))
        self.connection.last_select = (sql, params)

    def fetchone(self):
        sql, params = self.connection.last_select
        return self.connection.select_results.get((self.connection._normalize_sql(sql), params))

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instances = []
        self.select_results = {}
        self.last_select = ('', None)

    def cursor(self, **_kwargs):
        cursor = FakeCursor(self)
        self.cursor_instances.append(cursor)
        return cursor

    def add_select_result(self, sql: str, params, row):
        self.select_results[(self._normalize_sql(sql), params)] = row

    def _normalize_sql(self, sql: str) -> str:
        return ' '.join(sql.split())


class SettledTradeWatermarkRepositoryTest(unittest.TestCase):
    def test_loads_pool_market_watermark(self):
        connection = FakeConnection()
        repository = SettledTradeWatermarkRepository(connection)
        connection.add_select_result(
            '''
            SELECT MAX(trade_time_ms) AS market_watermark_ms
            FROM settled_trades
            WHERE pool_application_id = %s
            ''',
            ('pool-app',),
            {'market_watermark_ms': 1234},
        )

        watermark = repository.load_pool_market_watermark_ms('pool-app')

        self.assertEqual(watermark, 1234)
        self.assertIn('FROM settled_trades', connection.cursor_instances[0].executed[0][0])

    def test_returns_none_when_no_pool_trade_exists(self):
        connection = FakeConnection()
        repository = SettledTradeWatermarkRepository(connection)
        connection.add_select_result(
            '''
            SELECT MAX(trade_time_ms) AS market_watermark_ms
            FROM settled_trades
            WHERE pool_application_id = %s
            ''',
            ('pool-app',),
            {'market_watermark_ms': None},
        )

        self.assertIsNone(repository.load_pool_market_watermark_ms('pool-app'))


if __name__ == '__main__':
    unittest.main()
