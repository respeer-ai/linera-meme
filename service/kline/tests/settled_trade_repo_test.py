import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.settled_trade_repo import SettledTradeRepository  # noqa: E402


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
        self.commit_count = 0
        self.select_results = {}
        self.last_select = ('', None)

    def cursor(self, **_kwargs):
        cursor = FakeCursor(self)
        self.cursor_instances.append(cursor)
        return cursor

    def commit(self):
        self.commit_count += 1

    def add_select_result(self, sql: str, params, row):
        self.select_results[(self._normalize_sql(sql), params)] = row

    def _normalize_sql(self, sql: str) -> str:
        return ' '.join(sql.split())


class SettledTradeRepositoryTest(unittest.TestCase):
    def test_ensure_schema_creates_settled_trades_table(self):
        connection = FakeConnection()
        repository = SettledTradeRepository(connection)

        repository.ensure_schema()

        executed = connection.cursor_instances[0].executed
        executed_sql = executed[0][0]
        self.assertIn('CREATE TABLE IF NOT EXISTS settled_trades', executed_sql)
        self.assertIn('SELECT COLUMN_NAME FROM information_schema.COLUMNS', executed[1][0])
        self.assertIn('ADD COLUMN from_account', executed[2][0])
        self.assertIn('ADD COLUMN amount_0_in', executed[4][0])
        self.assertIn('ADD COLUMN amount_0_out', executed[6][0])
        self.assertIn('ADD COLUMN amount_1_in', executed[8][0])
        self.assertIn('ADD COLUMN amount_1_out', executed[10][0])
        self.assertEqual(connection.commit_count, 1)

    def test_ensure_schema_skips_alter_for_existing_columns(self):
        connection = FakeConnection()
        repository = SettledTradeRepository(connection)
        info_schema_sql = '''
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
            '''
        for column_name in (
            'from_account',
            'amount_0_in',
            'amount_0_out',
            'amount_1_in',
            'amount_1_out',
        ):
            connection.add_select_result(
                info_schema_sql,
                ('settled_trades', column_name),
                {'COLUMN_NAME': column_name},
            )

        repository.ensure_schema()

        executed_sql = '\n'.join(sql for sql, _params in connection.cursor_instances[0].executed)
        self.assertNotIn('ALTER TABLE settled_trades', executed_sql)
        self.assertEqual(connection.commit_count, 1)

    def test_upsert_settled_trades_persists_canonical_payload_json(self):
        connection = FakeConnection()
        repository = SettledTradeRepository(connection)

        count = repository.upsert_settled_trades(
            [
                {
                    'settled_trade_id': 'trade-1',
                    'normalized_event_id': 'event-1',
                    'pool_application_id': 'pool-app',
                    'pool_chain_id': 'pool-chain',
                    'from_account': 'user-chain:user-owner',
                    'block_hash': 'block-1',
                    'trade_time_ms': 1234,
                    'transaction_index': 7,
                    'transaction_id': 9,
                    'side': 'buy_token_0',
                    'amount_0_in': None,
                    'amount_0_out': '300',
                    'amount_1_in': '25',
                    'amount_1_out': None,
                    'amount_in': '25',
                    'amount_out': '300',
                    'price_numerator': '25',
                    'price_denominator': '300',
                    'source_event_key': 'event-1',
                    'event_payload_json': {'transaction': {'transaction_type': 'buy_token_0'}},
                }
            ]
        )

        self.assertEqual(count, 1)
        executed_sql, params = connection.cursor_instances[0].executed[0]
        self.assertIn('INSERT INTO settled_trades', executed_sql)
        self.assertEqual(
            params[4],
            'user-chain:user-owner',
        )
        self.assertEqual(
            params[10],
            None,
        )
        self.assertEqual(
            params[11],
            '300',
        )
        self.assertEqual(
            params[12],
            '25',
        )
        self.assertEqual(
            params[19],
            '{"transaction":{"transaction_type":"buy_token_0"}}',
        )
        self.assertEqual(connection.commit_count, 1)
