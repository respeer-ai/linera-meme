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
        self.rowcount = 0

    def execute(self, query, params=None):
        normalized = ' '.join(query.split())
        self.executed.append((normalized, params))
        self.rowcount = 0

        for prefix, error in self.connection.query_failures:
          if normalized.startswith(prefix):
              raise error

        if normalized == 'SHOW DATABASES':
          self._last_result = [(name,) for name in self.database_catalog]
          return

        if normalized == 'SHOW TABLES':
          self._last_result = [(name,) for name in self.table_catalog]
          return

        if normalized.startswith('SHOW COLUMNS FROM transactions'):
          self._last_result = [
              (name, 'varchar', 'NO' if name in self.connection.transaction_non_null_columns else 'YES')
              for name in self.connection.transaction_columns
          ]
          return

        if normalized.startswith('SHOW COLUMNS FROM candles'):
          self._last_result = [
              (name, 'varchar', 'NO' if name in self.connection.candle_non_null_columns else 'YES')
              for name in self.connection.candle_columns
          ]
          return

        if normalized.startswith('SHOW INDEX FROM '):
          table_name = normalized.split('SHOW INDEX FROM ')[1]
          self._last_result = [row for row in self.index_catalog if row[0] == table_name]
          return

        if normalized.startswith('SELECT COALESCE(DATA_LENGTH + INDEX_LENGTH, 0) AS table_bytes FROM information_schema.TABLES WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s'):
          self._last_result = [{
              'table_bytes': self.connection.get_table_bytes(params[1]),
          }] if self.dictionary else [(self.connection.get_table_bytes(params[1]),)]
          return

        if normalized.startswith('SELECT pool_id, pool_application FROM pools'):
          token_0 = normalized.split('token_0 = "')[1].split('"')[0]
          token_1 = normalized.split('token_1 = "')[1].split('"')[0]
          matches = [
              (pool['pool_id'], pool['pool_application'])
              for pool in self.connection.pool_rows.values()
              if pool['token_0'] == token_0 and pool['token_1'] == token_1
          ]
          self._last_result = matches
          return

        if normalized.startswith('SELECT pool_application, token_0, token_1 FROM pools WHERE pool_id = %s'):
          pool_id = params[0]
          pool = self.connection.pool_rows.get(pool_id)
          self._last_result = [] if pool is None else [
              (pool['pool_application'], pool['token_0'], pool['token_1'])
          ]
          return

        if normalized.startswith('SELECT pool_application FROM pools WHERE pool_id = %s'):
          pool_id = params[0]
          pool = self.connection.pool_rows.get(pool_id)
          self._last_result = [] if pool is None else [(pool['pool_application'],)]
          return

        if normalized.startswith('INSERT INTO pools VALUE'):
          pool_id, pool_application, token_0, token_1 = params
          self.connection.pool_rows[pool_id] = {
              'pool_id': pool_id,
              'pool_application': pool_application,
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

        if normalized.startswith('CREATE TABLE IF NOT EXISTS maker_events'):
          if 'maker_events' not in self.table_catalog:
              self.table_catalog.append('maker_events')
          self._last_result = []
          return

        if normalized.startswith('CREATE TABLE IF NOT EXISTS debug_traces'):
          if 'debug_traces' not in self.table_catalog:
              self.table_catalog.append('debug_traces')
          self._last_result = []
          return

        if normalized.startswith('ALTER TABLE transactions ADD COLUMN pool_application'):
          if 'pool_application' not in self.connection.transaction_columns:
              self.connection.transaction_columns.insert(0, 'pool_application')
          self._last_result = []
          return

        if normalized.startswith('ALTER TABLE candles ADD COLUMN pool_application'):
          if 'pool_application' not in self.connection.candle_columns:
              self.connection.candle_columns.insert(0, 'pool_application')
          self._last_result = []
          return

        if normalized.startswith('UPDATE pools SET pool_application = CONCAT("legacy:", pool_id) WHERE pool_application IS NULL'):
          for pool in self.connection.pool_rows.values():
              if pool.get('pool_application') is None:
                  pool['pool_application'] = f'legacy:{pool["pool_id"]}'
          self._last_result = []
          return

        if normalized.startswith('UPDATE transactions SET pool_application = CONCAT("legacy:", pool_id) WHERE pool_application IS NULL'):
          updated_rows = []
          for row in self.connection.transaction_rows:
              if self.connection.transaction_value(row, 'pool_application') is not None:
                  updated_rows.append(row)
                  continue

              row = list(row)
              columns = self.connection.transaction_columns
              row[columns.index('pool_application')] = f'legacy:{self.connection.transaction_value(row, "pool_id")}'
              updated_rows.append(tuple(row))
          self.connection.transaction_rows = updated_rows
          self._last_result = []
          return

        if normalized.startswith('UPDATE candles SET pool_application = CONCAT("legacy:", pool_id) WHERE pool_application IS NULL'):
          updated = {}
          for key, row in self.connection.candle_rows.items():
              if not isinstance(key, tuple):
                  continue
              if row.get('pool_application') is None:
                  row = row.copy()
                  row['pool_application'] = f'legacy:{row["pool_id"]}'
              updated_key = self.connection.candle_row_key(row)
              updated[updated_key] = row
              updated[(row['pool_id'], row['token_reversed'], row['interval_name'], row['bucket_start_ms'])] = row
          self.connection.candle_rows = updated
          self._last_result = []
          return

        if normalized.startswith('ALTER TABLE transactions MODIFY COLUMN pool_application VARCHAR(256) NOT NULL'):
          self.connection.transaction_non_null_columns.add('pool_application')
          self._last_result = []
          return

        if normalized.startswith('ALTER TABLE candles MODIFY COLUMN pool_application VARCHAR(256) NOT NULL'):
          self.connection.candle_non_null_columns.add('pool_application')
          self._last_result = []
          return

        if normalized.startswith('ALTER TABLE transactions DROP PRIMARY KEY'):
          self.index_catalog[:] = [row for row in self.index_catalog if row[2] != 'PRIMARY']
          self._last_result = []
          return

        if normalized.startswith('ALTER TABLE transactions ADD PRIMARY KEY'):
          self.index_catalog[:] = [row for row in self.index_catalog if row[2] != 'PRIMARY']
          self.index_catalog.extend([
              ('transactions', 0, 'PRIMARY', 1, 'pool_application'),
              ('transactions', 0, 'PRIMARY', 2, 'pool_id'),
              ('transactions', 0, 'PRIMARY', 3, 'transaction_id'),
              ('transactions', 0, 'PRIMARY', 4, 'token_reversed'),
          ])
          self._last_result = []
          return

        if normalized.startswith('ALTER TABLE candles DROP PRIMARY KEY'):
          self._last_result = []
          return

        if normalized.startswith('ALTER TABLE candles ADD PRIMARY KEY'):
          self._last_result = []
          return

        if normalized.startswith('DROP INDEX '):
          index_name = normalized.split('DROP INDEX ')[1].split(' ON ')[0]
          self.index_catalog[:] = [row for row in self.index_catalog if row[2] != index_name]
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

        if normalized.startswith('CREATE INDEX '):
          index_name = normalized.split('CREATE INDEX ')[1].split(' ON ')[0]
          table_name = normalized.split(' ON ')[1].split(' (')[0]
          columns = normalized.split(' (', 1)[1].rstrip(')').split(', ')
          self.index_catalog[:] = [row for row in self.index_catalog if row[2] != index_name]
          self.index_catalog.extend([
              (table_name, 1, index_name, seq + 1, column)
              for seq, column in enumerate(columns)
          ])
          self._last_result = []
          return

        if normalized.startswith('UPDATE transactions SET quote_volume = price * volume WHERE quote_volume IS NULL'):
          updated_rows = []
          for row in self.connection.transaction_rows:
              if self.connection.transaction_value(row, 'quote_volume') is None and self.connection.transaction_value(row, 'transaction_type') in {'BuyToken0', 'SellToken0'}:
                  row = list(row)
                  if len(row) == len(self.connection.transaction_columns):
                      columns = self.connection.transaction_columns
                  else:
                      columns = [column for column in self.connection.transaction_columns if column != 'pool_application']
                  quote_index = columns.index('quote_volume')
                  price_index = columns.index('price')
                  volume_index = columns.index('volume')
                  row[quote_index] = row[price_index] * row[volume_index]
                  row = tuple(row)
              updated_rows.append(row)
          self.connection.transaction_rows = updated_rows
          self._last_result = []
          return

        if normalized.startswith('INSERT IGNORE INTO transactions VALUES'):
          key = (params[0], params[1], params[2], params[14])
          existing_keys = {self.connection.transaction_row_key(row) for row in self.connection.transaction_rows}
          if key in existing_keys:
              self.rowcount = 0
              self._last_result = []
              return
          self.connection.transaction_rows.append(params)
          self.rowcount = 1
          self._last_result = []
          return

        if normalized.startswith('SELECT transaction_id, created_at, price, volume, quote_volume FROM transactions'):
          pool_application = normalized.split('WHERE pool_application = "')[1].split('"')[0]
          pool_id = int(normalized.split('AND pool_id = ')[1].split(' ')[0])
          token_reversed = normalized.split('AND token_reversed = ')[1].split(' ')[0] == 'True'
          start_at = int(normalized.split('AND created_at >= ')[1].split(' ')[0])
          end_at = int(normalized.split('AND created_at <= ')[1].split(' ')[0])
          rows = []
          for row in self.connection.transaction_rows:
              row_token_reversed = bool(self.connection.transaction_value(row, 'token_reversed'))
              row_created_at = self.connection.transaction_value(row, 'created_at')
              if self.connection.transaction_value(row, 'pool_application') != pool_application:
                  continue
              if self.connection.transaction_value(row, 'pool_id') != pool_id:
                  continue
              if row_token_reversed != token_reversed:
                  continue
              if self.connection.transaction_value(row, 'transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}:
                  continue
              if row_created_at < start_at or row_created_at > end_at:
                  continue
              rows.append({
                  'transaction_id': self.connection.transaction_value(row, 'transaction_id'),
                  'created_at': row_created_at,
                  'price': self.connection.transaction_value(row, 'price'),
                  'volume': self.connection.transaction_value(row, 'volume'),
                  'quote_volume': self.connection.transaction_value(row, 'quote_volume'),
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

        if normalized.startswith('SELECT t.pool_application, t.pool_id, p.token_0, p.token_1, t.from_account AS owner, COALESCE(SUM(CASE WHEN t.transaction_type = \'AddLiquidity\' THEN t.liquidity ELSE 0 END), 0) AS added_liquidity, COALESCE(SUM(CASE WHEN t.transaction_type = \'RemoveLiquidity\' THEN t.liquidity ELSE 0 END), 0) AS removed_liquidity, COALESCE(SUM(CASE WHEN t.transaction_type = \'AddLiquidity\' THEN 1 ELSE 0 END), 0) AS add_tx_count, COALESCE(SUM(CASE WHEN t.transaction_type = \'RemoveLiquidity\' THEN 1 ELSE 0 END), 0) AS remove_tx_count, MIN(CASE WHEN t.transaction_type = \'AddLiquidity\' THEN t.created_at ELSE NULL END) AS opened_at, MAX(t.created_at) AS updated_at FROM transactions t JOIN pools p ON p.pool_id = t.pool_id AND p.pool_application = t.pool_application WHERE t.from_account = %s AND t.transaction_type IN (\'AddLiquidity\', \'RemoveLiquidity\') GROUP BY t.pool_application, t.pool_id, p.token_0, p.token_1, t.from_account'):
          owner = params[0]
          grouped = {}
          for row in self.connection.transaction_rows:
              if self.connection.transaction_value(row, 'from_account') != owner:
                  continue
              transaction_type = self.connection.transaction_value(row, 'transaction_type')
              if transaction_type not in {'AddLiquidity', 'RemoveLiquidity'}:
                  continue
              pool_id = self.connection.transaction_value(row, 'pool_id')
              pool_application = self.connection.transaction_value(row, 'pool_application')
              pool = self.connection.pool_rows.get(pool_id)
              if pool is None or pool.get('pool_application') != pool_application:
                  continue

              key = (pool_application, pool_id, pool['token_0'], pool['token_1'], owner)
              current = grouped.get(key)
              created_at = self.connection.transaction_value(row, 'created_at')
              liquidity = self.connection.transaction_value(row, 'liquidity') or 0
              if current is None:
                  current = {
                      'pool_application': pool_application,
                      'pool_id': pool_id,
                      'token_0': pool['token_0'],
                      'token_1': pool['token_1'],
                      'owner': owner,
                      'added_liquidity': 0,
                      'removed_liquidity': 0,
                      'add_tx_count': 0,
                      'remove_tx_count': 0,
                      'opened_at': None,
                      'updated_at': None,
                  }
                  grouped[key] = current

              if transaction_type == 'AddLiquidity':
                  current['added_liquidity'] += liquidity
                  current['add_tx_count'] += 1
                  if current['opened_at'] is None or created_at < current['opened_at']:
                      current['opened_at'] = created_at
              elif transaction_type == 'RemoveLiquidity':
                  current['removed_liquidity'] += liquidity
                  current['remove_tx_count'] += 1

              if current['updated_at'] is None or created_at > current['updated_at']:
                  current['updated_at'] = created_at

          rows = list(grouped.values())
          rows.sort(key=lambda row: (row['pool_id'], row['pool_application']))
          self._last_result = rows if self.dictionary else [
              (
                  row['pool_application'],
                  row['pool_id'],
                  row['token_0'],
                  row['token_1'],
                  row['owner'],
                  row['added_liquidity'],
                  row['removed_liquidity'],
                  row['add_tx_count'],
                  row['remove_tx_count'],
                  row['opened_at'],
                  row['updated_at'],
              )
              for row in rows
          ]
          return

        if normalized.startswith('SELECT t.pool_id, t.pool_application, MAX(t.created_at) AS max_created_at FROM transactions t JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application GROUP BY t.pool_id, t.pool_application'):
          grouped = {}
          for row in self.connection.transaction_rows:
              pool_id = self.connection.transaction_value(row, 'pool_id')
              pool_application = self.connection.transaction_value(row, 'pool_application')
              if pool_id not in self.connection.pool_rows:
                  continue
              if self.connection.pool_rows[pool_id].get('pool_application') != pool_application:
                  continue
              created_at = self.connection.transaction_value(row, 'created_at')
              current = grouped.get((pool_id, pool_application))
              if current is None or created_at > current:
                  grouped[(pool_id, pool_application)] = created_at
          rows = [
              {'pool_id': pool_id, 'pool_application': pool_application, 'max_created_at': max_created_at}
              for (pool_id, pool_application), max_created_at in grouped.items()
          ]
          rows.sort(key=lambda item: (item['pool_id'], item['pool_application']))
          self._last_result = rows if self.dictionary else [
              (row['pool_id'], row['pool_application'], row['max_created_at']) for row in rows
          ]
          return

        if normalized.startswith('SELECT transaction_id, created_at, token_reversed FROM transactions WHERE pool_application = %s AND pool_id = %s AND created_at = %s ORDER BY transaction_id DESC, token_reversed DESC LIMIT 1'):
          pool_application, pool_id, created_at = params
          rows = []
          for row in self.connection.transaction_rows:
              row_created_at = self.connection.transaction_value(row, 'created_at')
              row_token_reversed = bool(self.connection.transaction_value(row, 'token_reversed'))
              if self.connection.transaction_value(row, 'pool_application') != pool_application:
                  continue
              if self.connection.transaction_value(row, 'pool_id') != pool_id or row_created_at != created_at:
                  continue
              rows.append({
                  'transaction_id': self.connection.transaction_value(row, 'transaction_id'),
                  'created_at': row_created_at,
                  'token_reversed': row_token_reversed,
              })
          rows.sort(key=lambda item: (item['transaction_id'], item['token_reversed']), reverse=True)
          selected = rows[:1]
          self._last_result = selected if self.dictionary else [
              (row['transaction_id'], row['created_at'], row['token_reversed']) for row in selected
          ]
          return

        if normalized.startswith('SELECT MIN(transaction_id) AS min_transaction_id, MAX(transaction_id) AS max_transaction_id FROM transactions WHERE pool_application = %s AND pool_id = %s AND token_reversed = 0'):
          pool_application, pool_id = params
          matching_ids = [
              self.connection.transaction_value(row, 'transaction_id')
              for row in self.connection.transaction_rows
              if self.connection.transaction_value(row, 'pool_application') == pool_application
              and self.connection.transaction_value(row, 'pool_id') == pool_id
              and bool(self.connection.transaction_value(row, 'token_reversed')) is False
          ]
          if len(matching_ids) == 0:
              row = {'min_transaction_id': None, 'max_transaction_id': None}
          else:
              row = {'min_transaction_id': min(matching_ids), 'max_transaction_id': max(matching_ids)}
          self._last_result = [row] if self.dictionary else [(row['min_transaction_id'], row['max_transaction_id'])]
          return

        if normalized.startswith('SELECT open, high, low, close, volume, quote_volume, trade_count, first_trade_id, last_trade_id, first_trade_at_ms, last_trade_at_ms FROM candles'):
          pool_application, pool_id, token_reversed, interval_name, bucket_start_ms = params
          row = next(
              (
                  value
                  for key, value in self.connection.candle_rows.items()
                  if self.connection.candle_matches(key, value, pool_application, pool_id, token_reversed, interval_name, bucket_start_ms)
              ),
              None,
          )
          if row is None:
              self._last_result = []
          elif self.dictionary:
              self._last_result = [row.copy()]
          else:
              self._last_result = [tuple(row.values())]
          return

        if normalized.startswith('SELECT bucket_start_ms, open, high, low, close, volume, quote_volume FROM candles'):
            pool_application, pool_id, token_reversed, interval_name, start_at, end_at = params
            rows = [
                row.copy()
                for key, row in self.connection.candle_rows.items()
                if self.connection.candle_matches(key, row, pool_application, pool_id, token_reversed, interval_name)
                and start_at <= row['bucket_start_ms'] <= end_at
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

        if normalized.startswith('SELECT bucket_start_ms, open, high, low, close, volume, quote_volume, trade_count, first_trade_id, last_trade_id, first_trade_at_ms, last_trade_at_ms FROM candles'):
            pool_application, pool_id, token_reversed, interval_name, before_bucket_start_ms = params
            rows = [
                row.copy()
                for key, row in self.connection.candle_rows.items()
                if self.connection.candle_matches(key, row, pool_application, pool_id, token_reversed, interval_name)
                and row['bucket_start_ms'] < before_bucket_start_ms
            ]
            rows.sort(key=lambda row: row['bucket_start_ms'], reverse=True)
            selected = rows[:1]
            if self.dictionary:
                self._last_result = selected
            else:
                self._last_result = [tuple(row.values()) for row in selected]
            return

        if normalized.startswith('INSERT INTO candles VALUES'):
          key = tuple(params[:5])
          row = {
              'pool_application': params[0],
              'pool_id': params[1],
              'token_reversed': params[2],
              'interval_name': params[3],
              'bucket_start_ms': params[4],
              'open': params[5],
              'high': params[6],
              'low': params[7],
              'close': params[8],
              'volume': params[9],
              'quote_volume': params[10],
              'trade_count': params[11],
              'first_trade_id': params[12],
              'last_trade_id': params[13],
              'first_trade_at_ms': params[14],
              'last_trade_at_ms': params[15],
          }
          self.connection.candle_rows[key] = row
          self.connection.candle_rows[(params[1], params[2], params[3], params[4])] = row
          self._last_result = []
          return

        if normalized.startswith('DELETE FROM candles WHERE pool_application = %s AND pool_id = %s AND token_reversed = %s AND interval_name = %s AND bucket_start_ms >= %s AND bucket_start_ms <= %s'):
          pool_application, pool_id, token_reversed, interval_name, start_at, end_at = params
          retained = {}
          for key, row in self.connection.candle_rows.items():
              if (
                  self.connection.candle_matches(key, row, pool_application, pool_id, token_reversed, interval_name)
                  and start_at <= row['bucket_start_ms'] <= end_at
              ):
                  continue
              retained[key] = row
          self.connection.candle_rows = retained
          self._last_result = []
          return

        if normalized.startswith('INSERT INTO maker_events (source, event_type, pool_id, token_0, token_1, amount_0, amount_1, quote_notional, pool_price, details, created_at) VALUES'):
          self.connection.maker_event_rows.append({
              'event_id': len(self.connection.maker_event_rows) + 1,
              'source': params[0],
              'event_type': params[1],
              'pool_id': params[2],
              'token_0': params[3],
              'token_1': params[4],
              'amount_0': params[5],
              'amount_1': params[6],
              'quote_notional': params[7],
              'pool_price': params[8],
              'details': params[9],
              'created_at': params[10],
          })
          self.rowcount = 1
          self._last_result = []
          return

        if normalized.startswith('SELECT event_id, source, event_type, pool_id, token_0, token_1, amount_0, amount_1, quote_notional, pool_price, details, created_at FROM maker_events WHERE created_at >= %s AND created_at <= %s ORDER BY created_at ASC, event_id ASC'):
          start_at, end_at = params
          rows = [
              row.copy()
              for row in self.connection.maker_event_rows
              if start_at <= row['created_at'] <= end_at
          ]
          rows.sort(key=lambda row: (row['created_at'], row['event_id']))
          self._last_result = rows if self.dictionary else [tuple(row.values()) for row in rows]
          return

        if normalized.startswith('SELECT event_id, source, event_type, pool_id, token_0, token_1, amount_0, amount_1, quote_notional, pool_price, details, created_at FROM maker_events WHERE token_0 = %s AND token_1 = %s AND created_at >= %s AND created_at <= %s ORDER BY created_at ASC, event_id ASC'):
          token_0, token_1, start_at, end_at = params
          rows = [
              row.copy()
              for row in self.connection.maker_event_rows
              if row['token_0'] == token_0
              and row['token_1'] == token_1
              and start_at <= row['created_at'] <= end_at
          ]
          rows.sort(key=lambda row: (row['created_at'], row['event_id']))
          self._last_result = rows if self.dictionary else [tuple(row.values()) for row in rows]
          return

        if normalized.startswith('SELECT COUNT(*) AS count, MAX(created_at) AS timestamp_begin, MIN(created_at) AS timestamp_end FROM maker_events WHERE token_0 = %s AND token_1 = %s'):
          token_0, token_1 = params
          rows = [
              row for row in self.connection.maker_event_rows
              if row['token_0'] == token_0 and row['token_1'] == token_1
          ]
          result = {
              'count': len(rows),
              'timestamp_begin': max((row['created_at'] for row in rows), default=None),
              'timestamp_end': min((row['created_at'] for row in rows), default=None),
          }
          self._last_result = [result] if self.dictionary else [tuple(result.values())]
          return

        if normalized.startswith('SELECT COUNT(*) AS count, MAX(created_at) AS timestamp_begin, MIN(created_at) AS timestamp_end FROM maker_events'):
          rows = list(self.connection.maker_event_rows)
          result = {
              'count': len(rows),
              'timestamp_begin': max((row['created_at'] for row in rows), default=None),
              'timestamp_end': min((row['created_at'] for row in rows), default=None),
          }
          self._last_result = [result] if self.dictionary else [tuple(result.values())]
          return

        if normalized.startswith('INSERT INTO debug_traces ( source, component, operation, target, owner, pool_application, pool_id, request_url, request_payload, response_status, response_body, error, details, created_at ) VALUES'):
          self.connection.debug_trace_rows.append({
              'trace_id': len(self.connection.debug_trace_rows) + 1,
              'source': params[0],
              'component': params[1],
              'operation': params[2],
              'target': params[3],
              'owner': params[4],
              'pool_application': params[5],
              'pool_id': params[6],
              'request_url': params[7],
              'request_payload': params[8],
              'response_status': params[9],
              'response_body': params[10],
              'error': params[11],
              'details': params[12],
              'created_at': params[13],
          })
          self.rowcount = 1
          self._last_result = []
          return

        if normalized.startswith('SELECT trace_id, request_payload, response_status, response_body, error, details FROM debug_traces'):
          rows = [row.copy() for row in self.connection.debug_trace_rows]
          older_than_ms, limit = params
          rows = [row for row in rows if row['created_at'] < older_than_ms]
          if '(error IS NOT NULL OR response_status >= 400)' in normalized:
              rows = [
                  row for row in rows
                  if row['error'] is not None or (row['response_status'] is not None and row['response_status'] >= 400)
              ]
          else:
              rows = [
                  row for row in rows
                  if row['error'] is None and (row['response_status'] is None or row['response_status'] < 400)
              ]
          rows.sort(key=lambda row: row['trace_id'])
          rows = rows[:limit]
          self._last_result = rows if self.dictionary else [
              (
                  row['trace_id'],
                  row['request_payload'],
                  row['response_status'],
                  row['response_body'],
                  row['error'],
                  row['details'],
              )
              for row in rows
          ]
          return

        if normalized.startswith('UPDATE debug_traces SET request_payload = %s, response_body = %s, details = %s WHERE trace_id = %s'):
          request_payload, response_body, details, trace_id = params
          updated_rows = []
          self.rowcount = 0
          for row in self.connection.debug_trace_rows:
              if row['trace_id'] != trace_id:
                  updated_rows.append(row)
                  continue
              updated_row = row.copy()
              updated_row['request_payload'] = request_payload
              updated_row['response_body'] = response_body
              updated_row['details'] = details
              updated_rows.append(updated_row)
              self.rowcount = 1
          self.connection.debug_trace_rows = updated_rows
          self._last_result = []
          return

        if normalized.startswith('DELETE FROM debug_traces WHERE created_at < %s AND error IS NULL AND (response_status IS NULL OR response_status < 400) AND MOD(trace_id, %s) != 0 ORDER BY trace_id ASC LIMIT %s'):
          older_than_ms, sample_mod, limit = params
          retained = []
          deleted = 0
          for row in sorted(self.connection.debug_trace_rows, key=lambda item: item['trace_id']):
              should_delete = (
                  row['created_at'] < older_than_ms
                  and row['error'] is None
                  and (row['response_status'] is None or row['response_status'] < 400)
                  and row['trace_id'] % sample_mod != 0
                  and deleted < limit
              )
              if should_delete:
                  deleted += 1
                  continue
              retained.append(row)
          self.connection.debug_trace_rows = retained
          self.rowcount = deleted
          self._last_result = []
          return

        if normalized.startswith('DELETE FROM debug_traces WHERE created_at < %s ORDER BY trace_id ASC LIMIT %s'):
          older_than_ms, limit = params
          retained = []
          deleted = 0
          for row in sorted(self.connection.debug_trace_rows, key=lambda item: item['trace_id']):
              should_delete = row['created_at'] < older_than_ms and deleted < limit
              if should_delete:
                  deleted += 1
                  continue
              retained.append(row)
          self.connection.debug_trace_rows = retained
          self.rowcount = deleted
          self._last_result = []
          return

        if normalized.startswith('OPTIMIZE TABLE debug_traces'):
          self.connection.optimized_tables.append('debug_traces')
          self._last_result = []
          return

        if normalized.startswith('SELECT trace_id, source, component, operation, target, owner, pool_application, pool_id, request_url, request_payload, response_status, response_body, error, details, created_at FROM debug_traces'):
          rows = [row.copy() for row in self.connection.debug_trace_rows]
          if 'WHERE ' in normalized:
              clauses = normalized.split('WHERE ')[1].split(' ORDER BY ')[0].split(' AND ')
              values = list(params[:-1])
              for clause in clauses:
                  value = values.pop(0)
                  if clause.endswith(' = %s'):
                      column = clause[:-5]
                      rows = [row for row in rows if row.get(column) == value]
                  elif clause.endswith(' >= %s'):
                      column = clause[:-6]
                      rows = [row for row in rows if row.get(column) is not None and row.get(column) >= value]
                  elif clause.endswith(' <= %s'):
                      column = clause[:-6]
                      rows = [row for row in rows if row.get(column) is not None and row.get(column) <= value]
          rows.sort(key=lambda row: row['trace_id'], reverse=True)
          rows = rows[:params[-1]]
          self._last_result = rows if self.dictionary else [tuple(row.values()) for row in rows]
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
        self.rollbacks = 0
        self.closed = False
        self.cursors = []
        self.pool_rows = {}
        self.transaction_rows = []
        self.candle_rows = {}
        self.maker_event_rows = []
        self.debug_trace_rows = []
        self.optimized_tables = []
        self.table_size_overrides = {}
        self.query_failures = []
        self.transaction_columns = [
            'pool_application', 'pool_id', 'transaction_id', 'transaction_type', 'from_account',
            'amount_0_in', 'amount_0_out', 'amount_1_in', 'amount_1_out',
            'liquidity', 'price', 'volume', 'quote_volume', 'direction',
            'token_reversed', 'created_at',
        ]
        self.transaction_non_null_columns = {'pool_id', 'transaction_id', 'token_reversed'}
        self.candle_columns = [
            'pool_application', 'pool_id', 'token_reversed', 'interval_name', 'bucket_start_ms',
            'open', 'high', 'low', 'close', 'volume', 'quote_volume',
            'trade_count', 'first_trade_id', 'last_trade_id', 'first_trade_at_ms', 'last_trade_at_ms',
        ]
        self.candle_non_null_columns = {'pool_id', 'token_reversed', 'interval_name', 'bucket_start_ms'}

    def transaction_value(self, row, column_name):
        if len(row) == len(self.transaction_columns):
            return row[self.transaction_columns.index(column_name)]

        legacy_columns = [column for column in self.transaction_columns if column != 'pool_application']
        if len(row) == len(legacy_columns) - 1:
            legacy_columns = [column for column in legacy_columns if column != 'quote_volume']
        if column_name == 'pool_application':
            pool_id = row[legacy_columns.index('pool_id')]
            pool = self.pool_rows.get(pool_id, {})
            return pool.get('pool_application')
        if column_name == 'quote_volume' and 'quote_volume' not in legacy_columns:
            return self.transaction_value(row, 'price') * self.transaction_value(row, 'volume')
        return row[legacy_columns.index(column_name)]

    def transaction_row_key(self, row):
        return (
            self.transaction_value(row, 'pool_application'),
            self.transaction_value(row, 'pool_id'),
            self.transaction_value(row, 'transaction_id'),
            self.transaction_value(row, 'token_reversed'),
        )

    def candle_row_key(self, row):
        return (
            row.get('pool_application'),
            row['pool_id'],
            row['token_reversed'],
            row['interval_name'],
            row['bucket_start_ms'],
        )

    def candle_matches(self, key, row, pool_application, pool_id, token_reversed, interval_name, bucket_start_ms=None):
        row_pool_application = row.get('pool_application')
        if row_pool_application is None and len(key) == 4 and pool_id in self.pool_rows:
            row_pool_application = self.pool_rows[pool_id].get('pool_application')

        row_pool_id = row['pool_id'] if 'pool_id' in row else key[-4]
        row_token_reversed = row['token_reversed'] if 'token_reversed' in row else key[-3]
        row_interval_name = row['interval_name'] if 'interval_name' in row else key[-2]
        row_bucket_start_ms = row['bucket_start_ms'] if 'bucket_start_ms' in row else key[-1]

        if row_pool_application != pool_application:
            return False
        if row_pool_id != pool_id:
            return False
        if row_token_reversed != token_reversed:
            return False
        if row_interval_name != interval_name:
            return False
        if bucket_start_ms is not None and row_bucket_start_ms != bucket_start_ms:
            return False
        return True

    def cursor(self, dictionary=False):
        cursor = FakeCursor(self.database_catalog, self.table_catalog, self.index_catalog)
        cursor.dictionary = dictionary
        cursor.connection = self
        self.cursors.append(cursor)
        return cursor

    def get_table_bytes(self, table_name):
        if table_name in self.table_size_overrides:
            return self.table_size_overrides[table_name]
        if table_name != 'debug_traces':
            return 0

        total = 0
        for row in self.debug_trace_rows:
            total += 256
            for field_name in ('source', 'component', 'operation', 'target', 'owner', 'pool_application', 'request_url', 'request_payload', 'response_body', 'error', 'details'):
                value = row.get(field_name)
                if value is None:
                    continue
                total += len(str(value).encode('utf-8'))
        return total

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1

    def ping(self, reconnect=True, attempts=1, delay=0):
        return None

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

    def create_connection_with_query_failure(self, prefix, error):
        connection = self.create_connection()
        connection.query_failures.append((prefix, error))
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
            'CREATE INDEX idx_transactions_pool_reverse_created_at ON transactions (pool_application, pool_id, token_reversed, created_at)'
            in query for query in executed_queries
        ))

    @patch('db.mysql.connector.connect')
    def test_does_not_recreate_range_query_index_when_present(self, connect_mock):
        self.index_catalog.extend([
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 1, 'pool_application'),
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 2, 'pool_id'),
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 3, 'token_reversed'),
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 4, 'created_at'),
        ])
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
            'CREATE INDEX idx_transactions_pool_reverse_created_at ON transactions (pool_application, pool_id, token_reversed, created_at)'
            in query for query in executed_queries
        ))

    @patch('db.mysql.connector.connect')
    def test_recreates_range_query_index_when_legacy_definition_is_present(self, connect_mock):
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

        self.assertTrue(any(
            f'DROP INDEX {Db.TRANSACTIONS_RANGE_INDEX} ON transactions' in query
            for query in executed_queries
        ))
        self.assertTrue(any(
            'CREATE INDEX idx_transactions_pool_reverse_created_at ON transactions (pool_application, pool_id, token_reversed, created_at)'
            in query for query in executed_queries
        ))

    @patch('db.mysql.connector.connect')
    def test_skips_debug_index_creation_when_table_is_full(self, connect_mock):
        class FakeTableFullError(Exception):
            def __init__(self):
                super().__init__("1114 (HY000): The table 'maker_events' is full")
                self.errno = 1114

        connect_mock.side_effect = lambda **kwargs: self.create_connection_with_query_failure(
            'CREATE INDEX idx_maker_events_created_event ON maker_events',
            FakeTableFullError(),
        )

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        self.assertIn('maker_events', db.debug_storage_degraded_tables)

        runtime_connection = self.connections[-1]
        executed_queries = [query for cursor in runtime_connection.cursors for query, _ in cursor.executed]
        self.assertTrue(any(
            'CREATE INDEX idx_maker_events_created_event ON maker_events (created_at, event_id)'
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
    def test_runtime_connection_enables_autocommit(self, connect_mock):
        connect_mock.side_effect = self.create_connection

        Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        runtime_call = connect_mock.call_args_list[-1]
        self.assertTrue(runtime_call.kwargs['autocommit'])


class DbReadFreshnessTest(unittest.TestCase):
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
        connection.pool_rows[1001] = {
            'pool_id': 1001,
            'pool_application': 'chain:app',
            'token_0': 'AAA',
            'token_1': 'BBB',
        }
        self.connections.append(connection)
        return connection

    @patch('db.mysql.connector.connect')
    def test_get_kline_rolls_back_before_reading(self, connect_mock):
        connect_mock.side_effect = self.create_connection

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        runtime_connection = self.connections[-1]
        runtime_connection.candle_rows[(1001, False, '1min', 1_800_000_000_000)] = {
            'pool_id': 1001,
            'token_reversed': False,
            'interval_name': '1min',
            'bucket_start_ms': 1_800_000_000_000,
            'open': 2.0,
            'high': 2.0,
            'low': 2.0,
            'close': 2.0,
            'volume': 1.0,
            'quote_volume': 2.0,
            'trade_count': 1,
            'first_trade_id': 1,
            'last_trade_id': 1,
            'first_trade_at_ms': 1_800_000_000_000,
            'last_trade_at_ms': 1_800_000_000_000,
        }

        db.get_kline('AAA', 'BBB', 1_800_000_000_000, 1_800_000_000_000, '1min')

        self.assertEqual(runtime_connection.rollbacks, 1)


class DbIdentityMigrationTest(unittest.TestCase):
    def setUp(self):
        self.database_catalog = ['kline']
        self.table_catalog = ['pools', 'transactions', 'candles']
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
        if len(self.connections) == 1:
            connection.pool_rows[7] = {
                'pool_id': 7,
                'pool_application': None,
                'token_0': 'AAA',
                'token_1': 'BBB',
            }
            connection.transaction_rows = [
                (
                    None, 7, 10, 'BuyToken0', 'chain:owner',
                    0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', False, 1_800_000_001_000,
                ),
            ]
            connection.candle_rows[(7, False, '1min', 1_800_000_000_000)] = {
                'pool_application': None,
                'pool_id': 7,
                'token_reversed': False,
                'interval_name': '1min',
                'bucket_start_ms': 1_800_000_000_000,
                'open': 2.0,
                'high': 2.0,
                'low': 2.0,
                'close': 2.0,
                'volume': 1.0,
                'quote_volume': 2.0,
                'trade_count': 1,
                'first_trade_id': 10,
                'last_trade_id': 10,
                'first_trade_at_ms': 1_800_000_000_000,
                'last_trade_at_ms': 1_800_000_000_000,
            }
        self.connections.append(connection)
        return connection

    @patch('db.mysql.connector.connect')
    def test_backfills_legacy_pool_application_before_switching_primary_keys(self, connect_mock):
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
        self.assertEqual(runtime_connection.pool_rows[7]['pool_application'], 'legacy:7')
        self.assertEqual(
            runtime_connection.transaction_value(runtime_connection.transaction_rows[0], 'pool_application'),
            'legacy:7',
        )
        candle = next(iter(runtime_connection.candle_rows.values()))
        self.assertEqual(candle['pool_application'], 'legacy:7')
        self.assertIn('pool_application', runtime_connection.transaction_non_null_columns)
        self.assertIn('pool_application', runtime_connection.candle_non_null_columns)


class DbMakerEventsQueryTest(unittest.TestCase):
    def setUp(self):
        self.database_catalog = ['kline']
        self.table_catalog = ['pools', 'transactions', 'candles', 'maker_events', 'debug_traces']
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

    @patch('db.mysql.connector.connect')
    def test_reads_maker_events_and_information(self, connect_mock):
        connect_mock.side_effect = self.create_connection

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        db.new_maker_event('planned', 1001, 'AAA', 'BBB', 1.0, 2.0, 2.0, 2.0, '{"step":1}', 1000)
        db.new_maker_event('executed', 1001, 'AAA', 'BBB', 3.0, 4.0, 4.0, 2.0, '{"step":2}', 2000)
        db.new_maker_event('planned', 1002, 'CCC', 'DDD', 5.0, 6.0, 6.0, 2.0, '{"step":3}', 3000)

        filtered = db.get_maker_events('AAA', 'BBB', 0, 2500)
        self.assertEqual([row['event_type'] for row in filtered], ['planned', 'executed'])

        combined = db.get_maker_events(None, None, 1500, 3500)
        self.assertEqual([row['pool_id'] for row in combined], [1001, 1002])

        info = db.get_maker_events_information('AAA', 'BBB')
        self.assertEqual(info['count'], 2)
        self.assertEqual(info['timestamp_begin'], 2000)
        self.assertEqual(info['timestamp_end'], 1000)

    @patch('db.mysql.connector.connect')
    def test_skips_maker_event_insert_when_table_is_full(self, connect_mock):
        class FakeTableFullError(Exception):
            def __init__(self):
                super().__init__("1114 (HY000): The table 'maker_events' is full")
                self.errno = 1114

        def connect_with_failure(**_kwargs):
            connection = FakeConnection(
                self.database_catalog,
                self.table_catalog,
                self.index_catalog,
            )
            connection.query_failures.append((
                'INSERT INTO maker_events (source, event_type, pool_id, token_0, token_1, amount_0, amount_1, quote_notional, pool_price, details, created_at) VALUES',
                FakeTableFullError(),
            ))
            self.connections.append(connection)
            return connection

        connect_mock.side_effect = connect_with_failure

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        db.new_maker_event('planned', 1001, 'AAA', 'BBB', 1.0, 2.0, 2.0, 2.0, '{"step":1}', 1000)

        self.assertEqual(db.get_maker_events('AAA', 'BBB', 0, 2000), [])
        self.assertIn('maker_events', db.debug_storage_degraded_tables)

    @patch('db.mysql.connector.connect')
    def test_records_and_reads_debug_traces(self, connect_mock):
        connect_mock.side_effect = self.create_connection

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        db.record_debug_trace(
            source='maker',
            component='swap',
            operation='swap',
            target='wallet_application_mutation',
            owner='chain:owner-a',
            pool_application='chain:pool-app',
            pool_id=7,
            request_url='http://wallet/chains/chain/applications/pool',
            request_payload={'query': 'mutation { swap }'},
            response_status=200,
            response_body='{"data":{"swap":true}}',
            error=None,
            details={'graphql_errors': None},
        )
        db.record_debug_trace(
            source='kline',
            component='swap',
            operation='get_pool_transactions',
            target='pool_query',
            owner=None,
            pool_application='chain:pool-app',
            pool_id=7,
            request_url='http://swap/query',
            request_payload={'query': 'query { latestTransactions }'},
            response_status=500,
            response_body='{"errors":["boom"]}',
            error='HTTP 500',
            details={'start_id': 1000},
        )

        maker_traces = db.get_debug_traces(source='maker', component='swap', limit=10)
        self.assertEqual(len(maker_traces), 1)
        self.assertEqual(maker_traces[0]['request_payload'], {'query': 'mutation { swap }'})
        self.assertEqual(maker_traces[0]['response_body'], {'data': {'swap': True}})

        all_traces = db.get_debug_traces(pool_application='chain:pool-app', pool_id=7, limit=10)
        self.assertEqual(len(all_traces), 2)
        self.assertEqual(all_traces[0]['error'], 'HTTP 500')

    @patch('db.mysql.connector.connect')
    def test_clips_large_success_debug_trace_payloads(self, connect_mock):
        connect_mock.side_effect = self.create_connection

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        db.record_debug_trace(
            source='kline',
            component='swap',
            operation='latest_transactions',
            target='pool_query',
            owner=None,
            pool_application='chain:pool-app',
            pool_id=7,
            request_url='http://swap/query',
            request_payload='x' * (Db.DEBUG_TRACES_SUCCESS_FIELD_LIMITS['request_payload'] + 512),
            response_status=200,
            response_body='y' * (Db.DEBUG_TRACES_SUCCESS_FIELD_LIMITS['response_body'] + 512),
            error=None,
            details={'payload': 'z' * (Db.DEBUG_TRACES_SUCCESS_FIELD_LIMITS['details'] + 512)},
        )

        traces = db.get_debug_traces(pool_application='chain:pool-app', pool_id=7, limit=10)
        self.assertEqual(len(traces), 1)
        self.assertIn('[truncated', traces[0]['request_payload'])
        self.assertIn('[truncated', traces[0]['response_body'])
        self.assertTrue(traces[0]['details']['_truncated'])
        self.assertEqual(traces[0]['details']['_field'], 'details')

    @patch('db.mysql.connector.connect')
    def test_debug_trace_cleanup_preserves_failure_rows_and_samples_old_successes(self, connect_mock):
        connect_mock.side_effect = self.create_connection

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        now_ms = 2_000_000_000_000
        db.now_ms = lambda: now_ms
        db.DEBUG_TRACES_MAX_BYTES = 20 * 1024
        runtime_connection = self.connections[-1]
        runtime_connection.debug_trace_rows = [
            {
                'trace_id': 1,
                'source': 'maker',
                'component': 'swap',
                'operation': 'swap',
                'target': 'wallet',
                'owner': 'chain:owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'request_url': 'http://wallet',
                'request_payload': 'a' * 9000,
                'response_status': 200,
                'response_body': 'b' * 9000,
                'error': None,
                'details': '{"note":"' + ('c' * 9000) + '"}',
                'created_at': now_ms - Db.DEBUG_TRACES_SUCCESS_RETENTION_MS - 1000,
            },
            {
                'trace_id': 25,
                'source': 'maker',
                'component': 'swap',
                'operation': 'swap',
                'target': 'wallet',
                'owner': 'chain:owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'request_url': 'http://wallet',
                'request_payload': 'd' * 9000,
                'response_status': 200,
                'response_body': 'e' * 9000,
                'error': None,
                'details': '{"note":"' + ('f' * 9000) + '"}',
                'created_at': now_ms - Db.DEBUG_TRACES_SUCCESS_RETENTION_MS - 1000,
            },
            {
                'trace_id': 26,
                'source': 'maker',
                'component': 'swap',
                'operation': 'swap',
                'target': 'wallet',
                'owner': 'chain:owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'request_url': 'http://wallet',
                'request_payload': 'g' * 9000,
                'response_status': 500,
                'response_body': 'h' * 500,
                'error': 'boom',
                'details': '{"note":"' + ('i' * 500) + '"}',
                'created_at': now_ms - Db.DEBUG_TRACES_SUCCESS_RETENTION_MS - 1000,
            },
        ]

        db._enforce_debug_trace_storage_budget(force=True)

        remaining_trace_ids = [row['trace_id'] for row in runtime_connection.debug_trace_rows]
        self.assertEqual(remaining_trace_ids, [25, 26])
        failure_row = next(row for row in runtime_connection.debug_trace_rows if row['trace_id'] == 26)
        sampled_success_row = next(row for row in runtime_connection.debug_trace_rows if row['trace_id'] == 25)
        self.assertIn('[truncated', sampled_success_row['response_body'])
        self.assertIn('debug_traces', runtime_connection.optimized_tables)

    @patch.dict('os.environ', {
        'KLINE_DEBUG_TRACES_MAX_BYTES': '2097152',
        'KLINE_DEBUG_TRACES_CLEANUP_INTERVAL_MS': '30000',
        'KLINE_DEBUG_TRACES_RECENT_FULL_MS': '600000',
        'KLINE_DEBUG_TRACES_SUCCESS_RETENTION_MS': '1200000',
        'KLINE_DEBUG_TRACES_FAILURE_RETENTION_MS': '2400000',
        'KLINE_DEBUG_TRACES_SUCCESS_SAMPLE_MOD': '10',
        'KLINE_DEBUG_TRACES_HARD_PRESSURE_SUCCESS_SAMPLE_MOD': '50',
        'KLINE_DEBUG_TRACES_CLEANUP_BATCH_SIZE': '123',
    }, clear=False)
    @patch('db.mysql.connector.connect')
    def test_debug_trace_runtime_config_and_storage_status(self, connect_mock):
        connect_mock.side_effect = self.create_connection

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        runtime_connection = self.connections[-1]
        runtime_connection.table_size_overrides['debug_traces'] = 512 * 1024
        db.last_debug_trace_cleanup_at_ms = 123456

        retention = db.get_debug_trace_retention_config()
        storage = db.get_debug_trace_storage_status()

        self.assertEqual(retention['max_bytes'], 2 * 1024 * 1024)
        self.assertEqual(retention['cleanup_interval_ms'], 30000)
        self.assertEqual(retention['recent_full_ms'], 600000)
        self.assertEqual(retention['success_retention_ms'], 1200000)
        self.assertEqual(retention['failure_retention_ms'], 2400000)
        self.assertEqual(retention['success_sample_mod'], 10)
        self.assertEqual(retention['hard_pressure_success_sample_mod'], 50)
        self.assertEqual(retention['cleanup_batch_size'], 123)
        self.assertEqual(storage['table_bytes'], 512 * 1024)
        self.assertEqual(storage['max_bytes'], 2 * 1024 * 1024)
        self.assertEqual(storage['last_cleanup_at_ms'], 123456)
        self.assertFalse(storage['over_budget'])
        self.assertAlmostEqual(storage['usage_ratio'], 0.25, places=6)

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
        self.assertEqual(runtime_connection.transaction_value(runtime_connection.transaction_rows[0], 'quote_volume'), 20.0)
        self.assertIsNone(runtime_connection.transaction_value(runtime_connection.transaction_rows[1], 'quote_volume'))


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
            pool_application='chain:app',
            pool_id=7,
            token_reversed=True,
            start_at=1_000_000,
            end_at=2_000_000,
        )

        self.assertIn('WHERE pool_application = "chain:app"', query)
        self.assertIn('AND pool_id = 7', query)
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

    @patch('db.mysql.connector.connect')
    def test_get_latest_transaction_watermarks_reads_latest_persisted_trade_per_pool(self, connect_mock):
        database_catalog = ['kline']
        table_catalog = ['pools', 'transactions', 'candles']
        index_catalog = []
        connections = []

        def create_connection(**_kwargs):
            connection = FakeConnection(database_catalog, table_catalog, index_catalog)
            if len(connections) == 1:
                connection.pool_rows[7] = {'pool_id': 7, 'pool_application': 'chain:app', 'token_0': 'AAA', 'token_1': 'BBB'}
                connection.pool_rows[8] = {'pool_id': 8, 'pool_application': 'chain:app-2', 'token_0': 'CCC', 'token_1': 'DDD'}
                connection.transaction_rows = [
                    (7, 10, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', False, 1_800_000_001_000),
                    (7, 11, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', True, 1_800_000_001_000),
                    (7, 12, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', False, 1_800_000_060_000),
                    (8, 3, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', False, 1_800_000_020_000),
                ]
            connections.append(connection)
            return connection

        connect_mock.side_effect = create_connection

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        self.assertEqual(
            db.get_latest_transaction_watermarks(),
            {
                (7, 'chain', 'app'): (1_800_000_060_000, 12, 0),
                (8, 'chain', 'app-2'): (1_800_000_020_000, 3, 0),
            },
        )

    @patch('db.mysql.connector.connect')
    def test_get_pool_transaction_id_bounds_reads_current_pool_application_only(self, connect_mock):
        database_catalog = ['kline']
        table_catalog = ['pools', 'transactions', 'candles']
        index_catalog = []
        connections = []

        def create_connection(**_kwargs):
            connection = FakeConnection(database_catalog, table_catalog, index_catalog)
            if len(connections) == 1:
                connection.pool_rows[7] = {'pool_id': 7, 'pool_application': 'chain:app', 'token_0': 'AAA', 'token_1': 'BBB'}
                connection.transaction_rows = [
                    ('legacy:7', 7, 1005, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', False, 1_800_000_001_000),
                    ('chain:app', 7, 1010, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', False, 1_800_000_002_000),
                    ('chain:app', 7, 1022, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', False, 1_800_000_003_000),
                    ('chain:app', 7, 1022, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', True, 1_800_000_003_000),
                ]
            connections.append(connection)
            return connection

        connect_mock.side_effect = create_connection

        db = Db(
            host='localhost',
            port=3306,
            db_name='kline',
            username='user',
            password='pass',
            clean_kline=False,
        )

        self.assertEqual(
            db.get_pool_transaction_id_bounds(7),
            {'min_transaction_id': 1010, 'max_transaction_id': 1022},
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
        pool_application = types.SimpleNamespace(chain_id='chain', owner='app')
        pool = types.SimpleNamespace(pool_id=7, token_0='AAA', token_1='BBB', pool_application=pool_application)
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
        self.assertEqual(runtime_connection.transaction_value(inserted, 'quote_volume'), row['quote_volume'])

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

    def test_rebuild_candles_from_transactions_overwrites_corrupted_bucket(self):
        db = self.create_db()
        self.seed_pool(db)
        runtime_connection = self.connections[-1]
        runtime_connection.transaction_rows = [
            (7, 10, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 2.0, 10.0, 20.0, 'Buy', False, 1_800_000_001_000),
            (7, 11, 'BuyToken0', 'chain:owner', 0, 0, 0, 0, 0, 3.0, 4.0, 12.0, 'Buy', False, 1_800_000_030_000),
        ]
        runtime_connection.candle_rows[(7, False, '1min', 1_800_000_000_000)] = {
            'pool_id': 7,
            'token_reversed': False,
            'interval_name': '1min',
            'bucket_start_ms': 1_800_000_000_000,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'volume': 30.0,
            'quote_volume': 50.0,
            'trade_count': 3,
            'first_trade_id': 10,
            'last_trade_id': 11,
            'first_trade_at_ms': 1_800_000_001_000,
            'last_trade_at_ms': 1_800_000_030_000,
        }

        rebuilt_count = db.rebuild_candles_from_transactions(
            pool_id=7,
            token_reversed=False,
            interval='1min',
            start_at=1_800_000_000_000,
            end_at=1_800_000_059_999,
        )

        rebuilt = runtime_connection.candle_rows[(7, False, '1min', 1_800_000_000_000)]
        self.assertEqual(rebuilt_count, 1)
        self.assertEqual(rebuilt['open'], 2.0)
        self.assertEqual(rebuilt['high'], 3.0)
        self.assertEqual(rebuilt['low'], 2.0)
        self.assertEqual(rebuilt['close'], 3.0)
        self.assertEqual(rebuilt['volume'], 14.0)
        self.assertEqual(rebuilt['quote_volume'], 32.0)
        self.assertEqual(rebuilt['trade_count'], 2)


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
            'pool_application': 'chain:app',
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
            _, _, token_0, token_1, points = db.get_kline(
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

    def test_get_kline_fills_internal_gaps_with_previous_close(self):
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
                'timestamp': 1_800_000_060_000,
                'bucket_start_ms': 1_800_000_060_000,
                'bucket_end_ms': 1_800_000_119_999,
                'is_final': True,
                'open': 2.5,
                'high': 2.5,
                'low': 2.5,
                'close': 2.5,
                'base_volume': 0.0,
                'quote_volume': 0.0,
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

    def test_get_kline_extends_gap_fill_beyond_latest_real_candle_with_zero_volume_buckets(self):
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
                'timestamp': 1_800_000_060_000,
                'bucket_start_ms': 1_800_000_060_000,
                'bucket_end_ms': 1_800_000_119_999,
                'is_final': True,
                'open': 2.5,
                'high': 2.5,
                'low': 2.5,
                'close': 2.5,
                'base_volume': 0.0,
                'quote_volume': 0.0,
            },
            {
                'timestamp': 1_800_000_120_000,
                'bucket_start_ms': 1_800_000_120_000,
                'bucket_end_ms': 1_800_000_179_999,
                'is_final': True,
                'open': 2.5,
                'high': 2.5,
                'low': 2.5,
                'close': 2.5,
                'base_volume': 0.0,
                'quote_volume': 0.0,
            },
            {
                'timestamp': 1_800_000_180_000,
                'bucket_start_ms': 1_800_000_180_000,
                'bucket_end_ms': 1_800_000_239_999,
                'is_final': True,
                'open': 2.5,
                'high': 2.5,
                'low': 2.5,
                'close': 2.5,
                'base_volume': 0.0,
                'quote_volume': 0.0,
            },
        ])

    def test_get_kline_fills_leading_empty_buckets_from_previous_close_when_available(self):
        db = self.create_db()
        connection = self.connections[-1]
        connection.candle_rows[(7, False, '1min', 1_799_999_940_000)] = {
            'pool_id': 7,
            'token_reversed': False,
            'interval_name': '1min',
            'bucket_start_ms': 1_799_999_940_000,
            'open': 1.8,
            'high': 2.1,
            'low': 1.7,
            'close': 2.0,
            'volume': 9.0,
            'quote_volume': 18.0,
            'trade_count': 2,
            'first_trade_id': 8,
            'last_trade_id': 9,
            'first_trade_at_ms': 1_799_999_941_000,
            'last_trade_at_ms': 1_799_999_959_000,
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
                'high': 2.0,
                'low': 2.0,
                'close': 2.0,
                'base_volume': 0.0,
                'quote_volume': 0.0,
            },
            {
                'timestamp': 1_800_000_060_000,
                'bucket_start_ms': 1_800_000_060_000,
                'bucket_end_ms': 1_800_000_119_999,
                'is_final': True,
                'open': 2.0,
                'high': 2.0,
                'low': 2.0,
                'close': 2.0,
                'base_volume': 0.0,
                'quote_volume': 0.0,
            },
            {
                'timestamp': 1_800_000_120_000,
                'bucket_start_ms': 1_800_000_120_000,
                'bucket_end_ms': 1_800_000_179_999,
                'is_final': True,
                'open': 2.0,
                'high': 2.0,
                'low': 2.0,
                'close': 2.0,
                'base_volume': 0.0,
                'quote_volume': 0.0,
            },
        ])

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
            _, _, _, _, points = db.get_kline(
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
            _, _, _, _, points = db.get_kline(
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
            {
                'timestamp': 1_800_000_120_000,
                'bucket_start_ms': 1_800_000_120_000,
                'bucket_end_ms': 1_800_000_179_999,
                'is_final': True,
                'open': 5.0,
                'high': 5.0,
                'low': 5.0,
                'close': 5.0,
                'base_volume': 0.0,
                'quote_volume': 0.0,
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
            _, _, _, _, points = db.get_kline(
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_000_000,
                interval='5min',
            )

        self.assertEqual(points[0]['bucket_end_ms'], 1_800_000_299_999)
        self.assertEqual(points[0]['is_final'], False)

    def test_get_kline_omits_current_unfinalized_empty_bucket_without_trades(self):
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

        with patch.object(db, 'now_ms', return_value=1_800_000_070_000):
            _, _, _, _, points = db.get_kline(
                token_0='AAA',
                token_1='BBB',
                start_at=1_800_000_000_000,
                end_at=1_800_000_060_000,
                interval='1min',
            )

        self.assertEqual(len(points), 1)
        self.assertEqual(points[0]['bucket_start_ms'], 1_800_000_000_000)


class DbPositionsQueryTest(unittest.TestCase):
    def setUp(self):
        self.database_catalog = ['kline']
        self.table_catalog = ['pools', 'transactions', 'candles']
        self.index_catalog = [
            ('transactions', 0, 'PRIMARY', 1, 'pool_id'),
            ('transactions', 0, 'PRIMARY', 2, 'transaction_id'),
            ('transactions', 0, 'PRIMARY', 3, 'token_reversed'),
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 1, 'pool_application'),
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 2, 'pool_id'),
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 3, 'token_reversed'),
            ('transactions', 1, Db.TRANSACTIONS_RANGE_INDEX, 4, 'created_at'),
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
            'pool_application': 'chain:app',
            'token_0': 'AAA',
            'token_1': 'BBB',
        }
        connection.pool_rows[8] = {
            'pool_id': 8,
            'pool_application': 'chain:app',
            'token_0': 'CCC',
            'token_1': 'DDD',
        }
        return db

    def transaction_row(
        self,
        pool_id,
        transaction_id,
        transaction_type,
        owner,
        liquidity,
        created_at,
        pool_application='chain:app',
    ):
        return (
            pool_application,
            pool_id,
            transaction_id,
            transaction_type,
            owner,
            0,
            0,
            0,
            0,
            liquidity,
            0,
            0,
            0,
            'Deposit' if transaction_type == 'AddLiquidity' else 'Burn',
            False,
            created_at,
        )

    def test_get_positions_returns_active_and_closed_positions(self):
        db = self.create_db()
        connection = self.connections[-1]
        connection.transaction_rows.extend([
            self.transaction_row(7, 10, 'AddLiquidity', 'chain:owner-a', 100, 1_800_000_001_000),
            self.transaction_row(7, 11, 'RemoveLiquidity', 'chain:owner-a', 40, 1_800_000_010_000),
            self.transaction_row(8, 12, 'AddLiquidity', 'chain:owner-a', 50, 1_800_000_020_000),
            self.transaction_row(8, 13, 'RemoveLiquidity', 'chain:owner-a', 50, 1_800_000_030_000),
            self.transaction_row(7, 14, 'AddLiquidity', 'chain:owner-b', 999, 1_800_000_040_000),
        ])

        positions = db.get_positions('chain:owner-a', status='all')

        self.assertEqual(len(positions), 2)
        self.assertEqual(
            positions,
            [
                {
                    'pool_application': 'chain:app',
                    'pool_id': 8,
                    'token_0': 'CCC',
                    'token_1': 'DDD',
                    'owner': 'chain:owner-a',
                    'status': 'closed',
                    'current_liquidity': '0',
                    'added_liquidity': '50',
                    'removed_liquidity': '50',
                    'add_tx_count': 1,
                    'remove_tx_count': 1,
                    'opened_at': 1_800_000_020_000,
                    'updated_at': 1_800_000_030_000,
                    'closed_at': 1_800_000_030_000,
                },
                {
                    'pool_application': 'chain:app',
                    'pool_id': 7,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': 'chain:owner-a',
                    'status': 'active',
                    'current_liquidity': '60',
                    'added_liquidity': '100',
                    'removed_liquidity': '40',
                    'add_tx_count': 1,
                    'remove_tx_count': 1,
                    'opened_at': 1_800_000_001_000,
                    'updated_at': 1_800_000_010_000,
                    'closed_at': None,
                },
            ],
        )

    def test_get_positions_filters_active_only(self):
        db = self.create_db()
        connection = self.connections[-1]
        connection.transaction_rows.extend([
            self.transaction_row(7, 10, 'AddLiquidity', 'chain:owner-a', 100, 1_800_000_001_000),
            self.transaction_row(8, 12, 'AddLiquidity', 'chain:owner-a', 50, 1_800_000_020_000),
            self.transaction_row(8, 13, 'RemoveLiquidity', 'chain:owner-a', 50, 1_800_000_030_000),
        ])

        positions = db.get_positions('chain:owner-a', status='active')

        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['pool_id'], 7)
        self.assertEqual(positions[0]['status'], 'active')

    def test_get_positions_filters_closed_only(self):
        db = self.create_db()
        connection = self.connections[-1]
        connection.transaction_rows.extend([
            self.transaction_row(7, 10, 'AddLiquidity', 'chain:owner-a', 100, 1_800_000_001_000),
            self.transaction_row(7, 11, 'RemoveLiquidity', 'chain:owner-a', 100, 1_800_000_010_000),
        ])

        positions = db.get_positions('chain:owner-a', status='closed')

        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['pool_id'], 7)
        self.assertEqual(positions[0]['status'], 'closed')
        self.assertEqual(positions[0]['closed_at'], 1_800_000_010_000)

    def test_get_positions_rejects_invalid_status(self):
        db = self.create_db()

        with self.assertRaises(ValueError):
            db.get_positions('chain:owner-a', status='bad')
