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

        if normalized.startswith('SHOW COLUMNS FROM transactions'):
          self._last_result = [(name,) for name in self.connection.transaction_columns]
          return

        if normalized.startswith('SHOW COLUMNS FROM candles'):
          self._last_result = [(name,) for name in self.connection.candle_columns]
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

        if normalized.startswith('ALTER TABLE transactions ADD COLUMN quote_volume'):
          if 'quote_volume' not in self.connection.transaction_columns:
              insert_at = self.connection.transaction_columns.index('volume') + 1
              self.connection.transaction_columns.insert(insert_at, 'quote_volume')
          self._last_result = []
          return

        if normalized.startswith('ALTER TABLE candles ADD COLUMN quote_volume'):
          if 'quote_volume' not in self.connection.candle_columns:
              insert_at = self.connection.candle_columns.index('volume') + 1
              self.connection.candle_columns.insert(insert_at, 'quote_volume')
          self._last_result = []
          return

        if normalized.startswith('UPDATE transactions SET quote_volume = price * volume WHERE quote_volume IS NULL'):
          updated_rows = []
          for row in self.connection.transaction_rows:
              if len(row) > 14:
                  if row[11] is None and row[2] in {'BuyToken0', 'SellToken0'}:
                      row = (
                          row[0], row[1], row[2], row[3], row[4],
                          row[5], row[6], row[7], row[8], row[9],
                          row[10], row[9] * row[10], row[12], row[13], row[14],
                      )
              updated_rows.append(row)
          self.connection.transaction_rows = updated_rows
          self._last_result = []
          return

        if normalized.startswith('INSERT INTO transactions VALUES'):
          self.connection.transaction_rows.append(params)
          self._last_result = []
          return

        if normalized.startswith('SELECT transaction_id, created_at, price, volume, quote_volume FROM transactions'):
          pool_id = int(normalized.split('WHERE pool_id = ')[1].split(' ')[0])
          token_reversed = normalized.split('AND token_reversed = ')[1].split(' ')[0] == 'True'
          start_at = int(normalized.split('AND created_at >= ')[1].split(' ')[0])
          end_at = int(normalized.split('AND created_at <= ')[1].split(' ')[0])
          rows = []
          for row in self.connection.transaction_rows:
              row_token_reversed = bool(row[13]) if len(row) > 14 else bool(row[12])
              row_created_at = row[14] if len(row) > 14 else row[13]
              if row[0] != pool_id:
                  continue
              if row_token_reversed != token_reversed:
                  continue
              if row[2] in {'AddLiquidity', 'RemoveLiquidity'}:
                  continue
              if row_created_at < start_at or row_created_at > end_at:
                  continue
              rows.append({
                  'transaction_id': row[1],
                  'created_at': row_created_at,
                  'price': row[9],
                  'volume': row[10],
                  'quote_volume': row[11] if len(row) > 14 else row[9] * row[10],
              })
          rows.sort(key=lambda item: (item['created_at'], item['transaction_id']))
          if self.dictionary:
              self._last_result = rows
          else:
              self._last_result = [
                  (row['transaction_id'], row['created_at'], row['price'], row['volume'], row['quote_volume'])
                  for row in rows
              ]
          return

        if normalized.startswith('SELECT open, high, low, close, volume, quote_volume, trade_count, first_trade_id, last_trade_id, first_trade_at_ms, last_trade_at_ms FROM candles'):
          key = tuple(params[:4])
          row = self.connection.candle_rows.get(key)
          if row is None:
              self._last_result = []
          elif self.dictionary:
              self._last_result = [row.copy()]
          else:
              self._last_result = [tuple(row.values())]
          return

        if normalized.startswith('SELECT bucket_start_ms, open, high, low, close, volume, quote_volume FROM candles'):
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
                      row.get('quote_volume'),
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
              'quote_volume': params[9],
              'trade_count': params[10],
              'first_trade_id': params[11],
              'last_trade_id': params[12],
              'first_trade_at_ms': params[13],
              'last_trade_at_ms': params[14],
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
        self.transaction_columns = [
            'pool_id', 'transaction_id', 'transaction_type', 'from_account',
            'amount_0_in', 'amount_0_out', 'amount_1_in', 'amount_1_out',
            'liquidity', 'price', 'volume', 'quote_volume', 'direction',
            'token_reversed', 'created_at',
        ]
        self.candle_columns = [
            'pool_id', 'token_reversed', 'interval_name', 'bucket_start_ms',
            'open', 'high', 'low', 'close', 'volume', 'quote_volume',
            'trade_count', 'first_trade_id', 'last_trade_id', 'first_trade_at_ms', 'last_trade_at_ms',
        ]

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

from db import Db, align_timestamp_to_minute_ms, build_kline_log_line, build_kline_points_query  # noqa: E402


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

    def base_volume(self, token_reversed: bool):
        return self._volume_reverse if token_reversed else self._volume_forward

    def quote_volume(self, token_reversed: bool):
        price = self.price(token_reversed)
        volume = self.base_volume(token_reversed)
        return price * volume

    def volume(self, token_reversed: bool):
        return self.base_volume(token_reversed)

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

    @patch('db.mysql.connector.connect')
    def test_backfills_missing_transaction_quote_volume_on_startup(self, connect_mock):
        def connect_with_seed(**_kwargs):
            connection = FakeConnection(
                self.database_catalog,
                self.table_catalog,
                self.index_catalog,
            )
            if len(self.connections) == 1:
                connection.transaction_rows = [
                    (
                        7, 10, 'BuyToken0', 'chain:owner',
                        0, 0, 0, 0, 0,
                        2.0, 10.0, None, 'Buy', False, 1_800_000_001_000,
                    ),
                    (
                        7, 11, 'AddLiquidity', 'chain:owner',
                        0, 0, 0, 0, 0,
                        3.0, 4.0, None, 'Deposit', False, 1_800_000_002_000,
                    ),
                ]
            self.connections.append(connection)
            return connection

        connect_mock.side_effect = connect_with_seed

        Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        runtime_connection = self.connections[-1]
        self.assertEqual(runtime_connection.transaction_rows[0][11], 20.0)
        self.assertIsNone(runtime_connection.transaction_rows[1][11])


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
        self.assertIn('SELECT transaction_id, created_at, price, volume, quote_volume FROM transactions', query)
        self.assertIn('ORDER BY created_at ASC, transaction_id ASC', query)

    def test_build_expected_bucket_count_aligns_to_interval_boundaries(self):
        from db import build_expected_bucket_count

        self.assertEqual(build_expected_bucket_count(1_800_000_000_000, 1_800_000_000_000, 60_000), 1)
        self.assertEqual(build_expected_bucket_count(1_800_000_000_000, 1_800_000_120_000, 60_000), 3)

    def test_build_kline_log_line_orders_fields_for_stable_grep(self):
        self.assertEqual(
            build_kline_log_line('request_complete', pool_id=7, source='candles', point_count=15),
            '[kline] event=request_complete point_count=15 pool_id=7 source=candles',
        )


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
        self.assertEqual(candle['quote_volume'], 32.0)
        self.assertEqual(candle['trade_count'], 2)
        self.assertEqual(candle['first_trade_id'], 10)
        self.assertEqual(candle['last_trade_id'], 11)

    def test_new_transaction_matches_transactions_table_column_count(self):
        db = self.create_db()
        self.seed_pool(db)

        transaction = FakeTransaction(
            transaction_id=10,
            created_at_ms=1_800_000_001_000,
        )

        row = db.new_transaction(7, transaction, False)

        runtime_connection = self.connections[-1]
        inserted = runtime_connection.transaction_rows[-1]
        self.assertEqual(len(inserted), len(runtime_connection.transaction_columns))
        self.assertEqual(inserted[11], row['quote_volume'])

    def test_save_candle_matches_candles_table_column_count(self):
        db = self.create_db()
        self.seed_pool(db)

        transaction = FakeTransaction(
            transaction_id=10,
            created_at_ms=1_800_000_001_000,
        )

        db.new_transaction(7, transaction, False)

        runtime_connection = self.connections[-1]
        inserted = runtime_connection.candle_rows[(7, False, '1min', 1_800_000_000_000)]
        self.assertEqual(len(inserted), len(runtime_connection.candle_columns))
        self.assertEqual(inserted['quote_volume'], 20.0)

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
        self.assertEqual(candle['quote_volume'], 20.0)
        self.assertEqual(candle['trade_count'], 1)
        self.assertEqual(candle['last_trade_id'], 10)

    def test_rebuilds_legacy_open_candle_before_appending_new_trade(self):
        db = self.create_db()
        self.seed_pool(db)
        runtime_connection = self.connections[-1]
        runtime_connection.transaction_rows.extend([
            (
                7, 10, 'BuyToken0', 'chain:owner',
                0, 0, 0, 0, 0,
                2.0, 10.0, 20.0, 'Buy', False, 1_800_000_001_000,
            ),
            (
                7, 11, 'SellToken0', 'chain:owner',
                0, 0, 0, 0, 0,
                3.0, 4.0, 12.0, 'Sell', False, 1_800_000_030_000,
            ),
        ])
        runtime_connection.candle_rows[(7, False, '1min', 1_800_000_000_000)] = {
            'pool_id': 7,
            'token_reversed': False,
            'interval_name': '1min',
            'bucket_start_ms': 1_800_000_000_000,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'volume': 14.0,
            'quote_volume': None,
            'trade_count': 2,
            'first_trade_id': 10,
            'last_trade_id': 11,
            'first_trade_at_ms': 1_800_000_001_000,
            'last_trade_at_ms': 1_800_000_030_000,
        }

        db.new_transactions(7, [
            FakeTransaction(
                transaction_id=12,
                created_at_ms=1_800_000_040_000,
                transaction_type='BuyToken0',
                price_forward=4.0,
                volume_forward=5.0,
            ),
        ])

        candle = runtime_connection.candle_rows[(7, False, '1min', 1_800_000_000_000)]
        self.assertEqual(candle['open'], 2.0)
        self.assertEqual(candle['high'], 4.0)
        self.assertEqual(candle['low'], 2.0)
        self.assertEqual(candle['close'], 4.0)
        self.assertEqual(candle['volume'], 19.0)
        self.assertEqual(candle['quote_volume'], 52.0)
        self.assertEqual(candle['trade_count'], 3)
        self.assertEqual(candle['first_trade_id'], 10)
        self.assertEqual(candle['last_trade_id'], 12)

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
        self.assertEqual(forward_candle['quote_volume'], 20.0)
        self.assertEqual(reverse_candle['open'], 0.5)
        self.assertEqual(reverse_candle['volume'], 20.0)
        self.assertEqual(reverse_candle['quote_volume'], 10.0)


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
            'quote_volume': 25.0,
            'trade_count': 2,
            'first_trade_id': 10,
            'last_trade_id': 11,
            'first_trade_at_ms': 1_800_000_001_000,
            'last_trade_at_ms': 1_800_000_030_000,
        }

        with patch.object(db, 'now_ms', return_value=1_800_000_200_000):
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
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_059_999,
            'is_final': True,
            'open': 2.0,
            'high': 3.0,
            'low': 1.5,
            'close': 2.5,
            'base_volume': 10.0,
            'quote_volume': 25.0,
        }])

    def test_get_kline_does_not_fill_internal_gaps_with_previous_close(self):
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
            'quote_volume': 25.0,
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
            'quote_volume': 15.6,
            'trade_count': 1,
            'first_trade_id': 12,
            'last_trade_id': 12,
            'first_trade_at_ms': 1_800_000_121_000,
            'last_trade_at_ms': 1_800_000_121_000,
        }

        with patch.object(db, 'now_ms', return_value=1_800_000_300_000):
            points = db.get_kline_from_candles(
                pool_id=7,
                token_reversed=False,
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_120_000,
                interval='1min',
            )

        self.assertEqual(points, [
            {
                'timestamp': 1_800_000_000_000,
                'bucket_start_ms': 1_800_000_000_000,
                'bucket_end_ms': 1_800_000_059_999,
                'is_final': True,
                'open': 2.0,
                'high': 3.0,
                'low': 1.5,
                'close': 2.5,
                'base_volume': 10.0,
                'quote_volume': 25.0,
            },
            {
                'timestamp': 1_800_000_120_000,
                'bucket_start_ms': 1_800_000_120_000,
                'bucket_end_ms': 1_800_000_179_999,
                'is_final': True,
                'open': 2.5,
                'high': 2.8,
                'low': 2.4,
                'close': 2.6,
                'base_volume': 6.0,
                'quote_volume': 15.6,
            },
        ])

    def test_get_kline_does_not_extend_gap_fill_beyond_latest_real_candle(self):
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
            'quote_volume': 25.0,
            'trade_count': 2,
            'first_trade_id': 10,
            'last_trade_id': 11,
            'first_trade_at_ms': 1_800_000_001_000,
            'last_trade_at_ms': 1_800_000_030_000,
        }

        with patch.object(db, 'now_ms', return_value=1_800_000_300_000):
            points = db.get_kline_from_candles(
                pool_id=7,
                token_reversed=False,
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_180_000,
                interval='1min',
            )

        self.assertEqual(points, [{
            'timestamp': 1_800_000_000_000,
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_059_999,
            'is_final': True,
            'open': 2.0,
            'high': 3.0,
            'low': 1.5,
            'close': 2.5,
            'base_volume': 10.0,
            'quote_volume': 25.0,
        }])

    def test_get_kline_from_candles_rejects_legacy_rows_without_quote_volume(self):
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
            'quote_volume': None,
            'trade_count': 2,
            'first_trade_id': 10,
            'last_trade_id': 11,
            'first_trade_at_ms': 1_800_000_001_000,
            'last_trade_at_ms': 1_800_000_030_000,
        }

        with patch.object(db, 'now_ms', return_value=1_800_000_200_000):
            points = db.get_kline_from_candles(
                pool_id=7,
                token_reversed=False,
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_000_000,
                interval='1min',
            )

        self.assertEqual(points, [])

    def test_get_kline_falls_back_to_transactions_only_when_no_candle_points_exist(self):
        db = self.create_db()

        with patch.object(db, 'get_kline_from_candles', return_value=[]) as candle_mock, patch.object(db, 'get_kline_from_transactions', return_value=[
            {
                'timestamp': 1_800_000_000_000,
                'open': 2.0,
                'high': 3.0,
                'low': 1.5,
                'close': 2.5,
                'base_volume': 10.0,
                'quote_volume': 25.0,
            },
            {
                'timestamp': 1_800_000_120_000,
                'open': 2.5,
                'high': 2.8,
                'low': 2.4,
                'close': 2.6,
                'base_volume': 6.0,
                'quote_volume': 15.600000000000001,
            },
            {
                'timestamp': 1_800_000_180_000,
                'open': 2.6,
                'high': 2.9,
                'low': 2.5,
                'close': 2.7,
                'base_volume': 5.0,
                'quote_volume': 13.5,
            },
        ]) as transaction_mock, patch.object(db, 'log_kline_event') as log_mock:
            _, _, points = db.get_kline(
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_180_000,
                interval='1min',
            )

        candle_mock.assert_called_once()
        transaction_mock.assert_called_once()
        self.assertEqual(
            [call.kwargs['event'] for call in log_mock.call_args_list],
            ['request_start', 'candles_result', 'transactions_fallback_start', 'transactions_result', 'request_complete'],
        )
        self.assertEqual(points[0]['timestamp'], 1_800_000_000_000)
        self.assertEqual(len(points), 3)

    def test_get_kline_prefers_sparse_candle_history_without_falling_back(self):
        db = self.create_db()
        candle_points = [
            {
                'timestamp': 1_800_000_120_000,
                'open': 2.5,
                'high': 2.8,
                'low': 2.4,
                'close': 2.6,
                'base_volume': 6.0,
                'quote_volume': 15.600000000000001,
            },
            {
                'timestamp': 1_800_000_180_000,
                'open': 2.6,
                'high': 2.9,
                'low': 2.5,
                'close': 2.7,
                'base_volume': 5.0,
                'quote_volume': 13.5,
            },
        ]

        with patch.object(db, 'get_kline_from_candles', return_value=candle_points) as candle_mock, patch.object(db, 'get_kline_from_transactions') as transaction_mock:
            _, _, points = db.get_kline(
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_180_000,
                interval='1min',
            )

        candle_mock.assert_called_once()
        transaction_mock.assert_not_called()
        self.assertEqual(points, candle_points)

    def test_get_kline_from_transactions_materializes_candles_for_historical_backfill(self):
        db = self.create_db()
        connection = self.connections[-1]
        connection.transaction_rows.extend([
            (
                7, 10, 'BuyToken0', 'chain:owner',
                0, 0, 0, 0, 0,
                2.0, 10.0, 'Buy', False, 1_800_000_001_000,
            ),
            (
                7, 11, 'SellToken0', 'chain:owner',
                0, 0, 0, 0, 0,
                3.0, 4.0, 'Sell', False, 1_800_000_030_000,
            ),
            (
                7, 12, 'BuyToken0', 'chain:owner',
                0, 0, 0, 0, 0,
                5.0, 6.0, 'Buy', False, 1_800_000_061_000,
            ),
        ])

        with patch.object(db, 'now_ms', return_value=1_800_000_300_000):
            points = db.get_kline_from_transactions(
                pool_id=7,
                token_reversed=False,
                start_at=1_800_000_000_000,
                end_at=1_800_000_120_000,
                interval='1min',
            )

        self.assertEqual(points, [
            {
                'timestamp': 1_800_000_000_000,
                'bucket_start_ms': 1_800_000_000_000,
                'bucket_end_ms': 1_800_000_059_999,
                'is_final': True,
                'open': 2.0,
                'high': 3.0,
                'low': 2.0,
                'close': 3.0,
                'base_volume': 14.0,
                'quote_volume': 32.0,
            },
            {
                'timestamp': 1_800_000_060_000,
                'bucket_start_ms': 1_800_000_060_000,
                'bucket_end_ms': 1_800_000_119_999,
                'is_final': True,
                'open': 5.0,
                'high': 5.0,
                'low': 5.0,
                'close': 5.0,
                'base_volume': 6.0,
                'quote_volume': 30.0,
            },
        ])
        self.assertIn((7, False, '1min', 1_800_000_000_000), connection.candle_rows)
        self.assertIn((7, False, '1min', 1_800_000_060_000), connection.candle_rows)

    def test_get_kline_uses_materialized_candles_after_transaction_backfill(self):
        db = self.create_db()
        connection = self.connections[-1]
        connection.transaction_rows.append(
            (
                7, 10, 'BuyToken0', 'chain:owner',
                0, 0, 0, 0, 0,
                2.0, 10.0, 'Buy', False, 1_800_000_001_000,
            ),
        )

        with patch.object(db, 'now_ms', return_value=1_800_000_300_000):
            first_points = db.get_kline(
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_060_000,
                interval='1min',
            )[2]

        with patch.object(db, 'get_kline_from_transactions') as transaction_mock, patch.object(db, 'now_ms', return_value=1_800_000_300_000):
            second_points = db.get_kline(
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_060_000,
                interval='1min',
            )[2]

        transaction_mock.assert_not_called()
        self.assertEqual(second_points, first_points)

    def test_get_kline_marks_latest_forming_bucket_explicitly(self):
        db = self.create_db()
        connection = self.connections[-1]
        connection.candle_rows[(7, False, '5min', 1_800_000_000_000)] = {
            'pool_id': 7,
            'token_reversed': False,
            'interval_name': '5min',
            'bucket_start_ms': 1_800_000_000_000,
            'open': 2.0,
            'high': 3.0,
            'low': 1.5,
            'close': 2.5,
            'volume': 10.0,
            'quote_volume': 25.0,
            'trade_count': 2,
            'first_trade_id': 10,
            'last_trade_id': 11,
            'first_trade_at_ms': 1_800_000_001_000,
            'last_trade_at_ms': 1_800_000_030_000,
        }

        with patch.object(db, 'now_ms', return_value=1_800_000_120_000):
            _, _, points = db.get_kline(
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_000_000,
                interval='5min',
            )

        self.assertEqual(points[0]['bucket_end_ms'], 1_800_000_299_999)
        self.assertEqual(points[0]['is_final'], False)
