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

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instances = []
        self.commit_count = 0

    def cursor(self, **_kwargs):
        cursor = FakeCursor(self)
        self.cursor_instances.append(cursor)
        return cursor

    def commit(self):
        self.commit_count += 1


class SettledTradeRepositoryTest(unittest.TestCase):
    def test_ensure_schema_creates_settled_trades_table(self):
        connection = FakeConnection()
        repository = SettledTradeRepository(connection)

        repository.ensure_schema()

        executed_sql = connection.cursor_instances[0].executed[0][0]
        self.assertIn('CREATE TABLE IF NOT EXISTS settled_trades', executed_sql)
        alter_sql = connection.cursor_instances[0].executed[1][0]
        self.assertIn('ADD COLUMN IF NOT EXISTS from_account', alter_sql)
        self.assertIn('ADD COLUMN IF NOT EXISTS amount_0_in', connection.cursor_instances[0].executed[2][0])
        self.assertIn('ADD COLUMN IF NOT EXISTS amount_0_out', connection.cursor_instances[0].executed[3][0])
        self.assertIn('ADD COLUMN IF NOT EXISTS amount_1_in', connection.cursor_instances[0].executed[4][0])
        self.assertIn('ADD COLUMN IF NOT EXISTS amount_1_out', connection.cursor_instances[0].executed[5][0])
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
