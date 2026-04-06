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
        self.connection = None

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

        if normalized.startswith('SELECT pool_id FROM pools'):
          token_0 = normalized.split('token_0 = "')[1].split('"')[0]
          token_1 = normalized.split('token_1 = "')[1].split('"')[0]
          matches = [
              (pool['pool_id'],)
              for pool in self.connection.pool_rows.values()
              if pool['token_0'] == token_0 and pool['token_1'] == token_1
          ]
          self._last_result = matches
          return

        if normalized.startswith('INSERT INTO pools VALUE'):
          pool_id, token_0, token_1 = params
          self.connection.pool_rows[pool_id] = {
              'pool_id': pool_id,
              'token_0': token_0,
              'token_1': token_1,
          }
          self._last_result = []
          return

        if normalized.startswith('CREATE TABLE IF NOT EXISTS candles'):
          if 'candles' not in self.table_catalog:
              self.table_catalog.append('candles')
          self._last_result = []
          return

        if normalized.startswith('INSERT INTO transactions VALUES'):
          self.connection.transaction_rows.append(params)
          self._last_result = []
          return

        if normalized.startswith('SELECT open, high, low, close, volume, trade_count, first_trade_id, last_trade_id, first_trade_at_ms, last_trade_at_ms FROM candles'):
          key = tuple(params[:4])
          row = self.connection.candle_rows.get(key)
          if row is None:
              self._last_result = []
          elif self.dictionary:
              self._last_result = [row.copy()]
          else:
              self._last_result = [tuple(row.values())]
          return

        if normalized.startswith('SELECT bucket_start_ms, open, high, low, close, volume FROM candles'):
          pool_id, token_reversed, interval_name, start_at, end_at = params
          rows = [
              row.copy()
              for key, row in self.connection.candle_rows.items()
              if key[0] == pool_id
              and key[1] == token_reversed
              and key[2] == interval_name
              and start_at <= key[3] <= end_at
          ]
          rows.sort(key=lambda row: row['bucket_start_ms'])
          if self.dictionary:
              self._last_result = rows
          else:
              self._last_result = [
                  (
                      row['bucket_start_ms'],
                      row['open'],
                      row['high'],
                      row['low'],
                      row['close'],
                      row['volume'],
                  )
                  for row in rows
              ]
          return

        if normalized.startswith('INSERT INTO candles VALUES'):
          key = tuple(params[:4])
          self.connection.candle_rows[key] = {
              'pool_id': params[0],
              'token_reversed': params[1],
              'interval_name': params[2],
              'bucket_start_ms': params[3],
              'open': params[4],
              'high': params[5],
              'low': params[6],
              'close': params[7],
              'volume': params[8],
              'trade_count': params[9],
              'first_trade_id': params[10],
              'last_trade_id': params[11],
              'first_trade_at_ms': params[12],
              'last_trade_at_ms': params[13],
          }
          self._last_result = []
          return

        self._last_result = []

    def fetchall(self):
        return list(self._last_result)

    def fetchone(self):
        return self._last_result[0] if self._last_result else None

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
        self.pool_rows = {}
        self.transaction_rows = []
        self.candle_rows = {}

    def cursor(self, dictionary=False):
        cursor = FakeCursor(self.database_catalog, self.table_catalog, self.index_catalog)
        cursor.dictionary = dictionary
        cursor.connection = self
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


class FakeFromAccount:
    def __init__(self, chain_id='chain', owner='owner'):
        self.chain_id = chain_id
        self.owner = owner


class FakeTransaction:
    def __init__(
        self,
        transaction_id,
        created_at_ms,
        transaction_type='BuyToken0',
        price_forward=2.0,
        volume_forward=10.0,
        price_reverse=0.5,
        volume_reverse=20.0,
    ):
        self.transaction_id = transaction_id
        self.transaction_type = transaction_type
        self.from_ = FakeFromAccount()
        self.amount_0_in = 0
        self.amount_0_out = 0
        self.amount_1_in = 0
        self.amount_1_out = 0
        self.liquidity = 0
        self.created_at = created_at_ms * 1000
        self._price_forward = price_forward
        self._volume_forward = volume_forward
        self._price_reverse = price_reverse
        self._volume_reverse = volume_reverse

    def direction(self, token_reversed: bool):
        if self.transaction_type == 'BuyToken0':
            return 'Buy' if token_reversed is False else 'Sell'
        if self.transaction_type == 'SellToken0':
            return 'Sell' if token_reversed is False else 'Buy'
        if self.transaction_type == 'AddLiquidity':
            return 'Deposit'
        if self.transaction_type == 'RemoveLiquidity':
            return 'Burn'
        raise Exception('Invalid transaction type')

    def price(self, token_reversed: bool):
        return self._price_reverse if token_reversed else self._price_forward

    def volume(self, token_reversed: bool):
        return self._volume_reverse if token_reversed else self._volume_forward

    def record_reverse(self):
        return self.transaction_type in {'BuyToken0', 'SellToken0'}


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

    @patch('db.mysql.connector.connect')
    def test_creates_candles_table_when_missing(self, connect_mock):
        self.table_catalog = ['pools', 'transactions']
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
            'CREATE TABLE IF NOT EXISTS candles' in query for query in executed_queries
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


class DbCandleIngestTest(unittest.TestCase):
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

    def create_db(self):
        with patch('db.mysql.connector.connect') as connect_mock:
            connect_mock.side_effect = self.create_connection
            return Db(
                host='localhost',
                port=3306,
                db_name='kline',
                username='user',
                password='pass',
                clean_kline=False,
            )

    def seed_pool(self, db):
        pool = types.SimpleNamespace(pool_id=7, token_0='AAA', token_1='BBB')
        db.new_pools([pool])

    def test_creates_and_updates_candle_in_same_bucket(self):
        db = self.create_db()
        self.seed_pool(db)

        first_trade = FakeTransaction(
            transaction_id=10,
            created_at_ms=1_800_000_001_000,
            price_forward=2.0,
            volume_forward=10.0,
            price_reverse=0.5,
            volume_reverse=20.0,
        )
        second_trade = FakeTransaction(
            transaction_id=11,
            created_at_ms=1_800_000_030_000,
            price_forward=3.0,
            volume_forward=4.0,
            price_reverse=0.333333333333,
            volume_reverse=12.0,
        )

        db.new_transactions(7, [first_trade, second_trade])

        runtime_connection = self.connections[-1]
        candle = runtime_connection.candle_rows[(7, False, '1min', 1_800_000_000_000)]

        self.assertEqual(candle['open'], 2.0)
        self.assertEqual(candle['high'], 3.0)
        self.assertEqual(candle['low'], 2.0)
        self.assertEqual(candle['close'], 3.0)
        self.assertEqual(candle['volume'], 14.0)
        self.assertEqual(candle['trade_count'], 2)
        self.assertEqual(candle['first_trade_id'], 10)
        self.assertEqual(candle['last_trade_id'], 11)

    def test_rolls_over_to_next_bucket_when_trade_crosses_interval_boundary(self):
        db = self.create_db()
        self.seed_pool(db)

        db.new_transactions(7, [
            FakeTransaction(transaction_id=10, created_at_ms=1_800_000_001_000),
            FakeTransaction(transaction_id=11, created_at_ms=1_800_000_060_000),
        ])

        runtime_connection = self.connections[-1]

        self.assertIn((7, False, '1min', 1_800_000_000_000), runtime_connection.candle_rows)
        self.assertIn((7, False, '1min', 1_800_000_060_000), runtime_connection.candle_rows)

    def test_ignores_replayed_trade_for_idempotent_candle_updates(self):
        db = self.create_db()
        self.seed_pool(db)
        trade = FakeTransaction(transaction_id=10, created_at_ms=1_800_000_001_000)

        db.new_transactions(7, [trade])
        db.new_transactions(7, [trade])

        runtime_connection = self.connections[-1]
        candle = runtime_connection.candle_rows[(7, False, '1min', 1_800_000_000_000)]

        self.assertEqual(candle['volume'], 10.0)
        self.assertEqual(candle['trade_count'], 1)
        self.assertEqual(candle['last_trade_id'], 10)

    def test_records_reverse_direction_candles_with_reverse_price_and_volume(self):
        db = self.create_db()
        self.seed_pool(db)

        db.new_transactions(7, [
            FakeTransaction(
                transaction_id=10,
                created_at_ms=1_800_000_001_000,
                price_forward=2.0,
                volume_forward=10.0,
                price_reverse=0.5,
                volume_reverse=20.0,
            ),
        ])

        runtime_connection = self.connections[-1]
        forward_candle = runtime_connection.candle_rows[(7, False, '5min', 1_800_000_000_000)]
        reverse_candle = runtime_connection.candle_rows[(7, True, '5min', 1_800_000_000_000)]

        self.assertEqual(forward_candle['open'], 2.0)
        self.assertEqual(forward_candle['volume'], 10.0)
        self.assertEqual(reverse_candle['open'], 0.5)
        self.assertEqual(reverse_candle['volume'], 20.0)


class DbCandleQueryTest(unittest.TestCase):
    def setUp(self):
        self.database_catalog = ['kline']
        self.table_catalog = ['pools', 'transactions', 'candles']
        self.index_catalog = [
            ('transactions', 0, 'PRIMARY', 1, 'pool_id'),
            ('transactions', 0, 'PRIMARY', 2, 'transaction_id'),
            ('transactions', 0, 'PRIMARY', 3, 'token_reversed'),
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 1, 'pool_id'),
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

    def create_db(self):
        with patch('db.mysql.connector.connect') as connect_mock:
            connect_mock.side_effect = self.create_connection
            db = Db(
                host='localhost',
                port=3306,
                db_name='kline',
                username='user',
                password='pass',
                clean_kline=False,
            )
        connection = self.connections[-1]
        connection.pool_rows[7] = {
            'pool_id': 7,
            'token_0': 'AAA',
            'token_1': 'BBB',
        }
        return db

    def test_get_kline_reads_preaggregated_candles_instead_of_raw_pandas_path(self):
        db = self.create_db()
        connection = self.connections[-1]
        connection.candle_rows[(7, False, '1min', 1_800_000_000_000)] = {
            'pool_id': 7,
            'token_reversed': False,
            'interval_name': '1min',
            'bucket_start_ms': 1_800_000_000_000,
            'open': 2.0,
            'high': 3.0,
            'low': 1.5,
            'close': 2.5,
            'volume': 10.0,
            'trade_count': 2,
            'first_trade_id': 10,
            'last_trade_id': 11,
            'first_trade_at_ms': 1_800_000_001_000,
            'last_trade_at_ms': 1_800_000_030_000,
        }

        token_0, token_1, points = db.get_kline(
            token_0='AAA',
            token_1='BBB',
            start_at=1_800_000_000_000,
            end_at=1_800_000_000_000,
            interval='1min',
        )

        self.assertEqual((token_0, token_1), ('AAA', 'BBB'))
        self.assertEqual(points, [{
            'timestamp': 1_800_000_000_000,
            'open': 2.0,
            'high': 3.0,
            'low': 1.5,
            'close': 2.5,
            'volume': 10.0,
        }])

    def test_get_kline_preserves_gap_fill_with_previous_close(self):
        db = self.create_db()
        connection = self.connections[-1]
        connection.candle_rows[(7, False, '1min', 1_800_000_000_000)] = {
            'pool_id': 7,
            'token_reversed': False,
            'interval_name': '1min',
            'bucket_start_ms': 1_800_000_000_000,
            'open': 2.0,
            'high': 3.0,
            'low': 1.5,
            'close': 2.5,
            'volume': 10.0,
            'trade_count': 2,
            'first_trade_id': 10,
            'last_trade_id': 11,
            'first_trade_at_ms': 1_800_000_001_000,
            'last_trade_at_ms': 1_800_000_030_000,
        }
        connection.candle_rows[(7, False, '1min', 1_800_000_120_000)] = {
            'pool_id': 7,
            'token_reversed': False,
            'interval_name': '1min',
            'bucket_start_ms': 1_800_000_120_000,
            'open': 2.5,
            'high': 2.8,
            'low': 2.4,
            'close': 2.6,
            'volume': 6.0,
            'trade_count': 1,
            'first_trade_id': 12,
            'last_trade_id': 12,
            'first_trade_at_ms': 1_800_000_121_000,
            'last_trade_at_ms': 1_800_000_121_000,
        }

        _, _, points = db.get_kline(
            token_0='AAA',
            token_1='BBB',
            start_at=1_800_000_000_000,
            end_at=1_800_000_120_000,
            interval='1min',
        )

        self.assertEqual(points, [
            {
                'timestamp': 1_800_000_000_000,
                'open': 2.0,
                'high': 3.0,
                'low': 1.5,
                'close': 2.5,
                'volume': 10.0,
            },
            {
                'timestamp': 1_800_000_060_000,
                'open': 2.5,
                'high': 2.5,
                'low': 2.5,
                'close': 2.5,
                'volume': 0.0,
            },
            {
                'timestamp': 1_800_000_120_000,
                'open': 2.5,
                'high': 2.8,
                'low': 2.4,
                'close': 2.6,
                'volume': 6.0,
            },
        ])

    def test_get_kline_falls_back_when_candle_history_is_incomplete(self):
        db = self.create_db()

        with patch.object(db, 'get_kline_from_candles', return_value=[
            {
                'timestamp': 1_800_000_120_000,
                'open': 2.5,
                'high': 2.8,
                'low': 2.4,
                'close': 2.6,
                'volume': 6.0,
            },
            {
                'timestamp': 1_800_000_180_000,
                'open': 2.6,
                'high': 2.9,
                'low': 2.5,
                'close': 2.7,
                'volume': 5.0,
            },
        ]) as candle_mock, patch.object(db, 'get_kline_from_transactions', return_value=[
            {
                'timestamp': 1_800_000_000_000,
                'open': 2.0,
                'high': 3.0,
                'low': 1.5,
                'close': 2.5,
                'volume': 10.0,
            },
            {
                'timestamp': 1_800_000_060_000,
                'open': 2.5,
                'high': 2.5,
                'low': 2.5,
                'close': 2.5,
                'volume': 0.0,
            },
            {
                'timestamp': 1_800_000_120_000,
                'open': 2.5,
                'high': 2.8,
                'low': 2.4,
                'close': 2.6,
                'volume': 6.0,
            },
            {
                'timestamp': 1_800_000_180_000,
                'open': 2.6,
                'high': 2.9,
                'low': 2.5,
                'close': 2.7,
                'volume': 5.0,
            },
        ]) as transaction_mock:
            _, _, points = db.get_kline(
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_180_000,
                interval='1min',
            )

        candle_mock.assert_called_once()
        transaction_mock.assert_called_once()
        self.assertEqual(points[0]['timestamp'], 1_800_000_000_000)
        self.assertEqual(len(points), 4)
