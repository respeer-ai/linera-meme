import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.settled_liquidity_change_repo import SettledLiquidityChangeRepository  # noqa: E402


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.executed = []
        self.closed = False

    def execute(self, sql: str, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        return None

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


class SettledLiquidityChangeRepositoryTest(unittest.TestCase):
    def test_ensure_schema_creates_settled_liquidity_changes_table(self):
        connection = FakeConnection()
        repository = SettledLiquidityChangeRepository(connection)

        repository.ensure_schema()

        executed_sql = '\n'.join(sql for sql, _params in connection.cursor_instances[0].executed)
        self.assertIn('CREATE TABLE IF NOT EXISTS settled_liquidity_changes', executed_sql)
        self.assertIn('is_position_liquidity BOOLEAN', executed_sql)
        self.assertIn('liquidity_semantics VARCHAR(64)', executed_sql)
        self.assertEqual(connection.commit_count, 1)

    def test_upsert_settled_liquidity_changes_persists_canonical_payload_json(self):
        connection = FakeConnection()
        repository = SettledLiquidityChangeRepository(connection)

        count = repository.upsert_settled_liquidity_changes(
            [
                {
                    'settled_liquidity_change_id': 'change-1',
                    'normalized_event_id': 'event-2',
                    'pool_application_id': 'pool-app',
                    'pool_chain_id': 'pool-chain',
                    'owner': 'owner@chain',
                    'block_hash': 'block-2',
                    'event_time_ms': 5678,
                    'transaction_index': 8,
                    'transaction_id': 10,
                    'change_type': 'add_liquidity',
                    'liquidity_delta': '888',
                    'is_position_liquidity': True,
                    'liquidity_semantics': 'position_liquidity',
                    'amount_0_delta': '1000',
                    'amount_1_delta': '55',
                    'source_event_key': 'event-2',
                    'event_payload_json': {'transaction': {'transaction_type': 'add_liquidity'}},
                }
            ]
        )

        self.assertEqual(count, 1)
        executed_sql, params = connection.cursor_instances[0].executed[0]
        self.assertIn('INSERT INTO settled_liquidity_changes', executed_sql)
        self.assertEqual(
            params[16],
            '{"transaction":{"transaction_type":"add_liquidity"}}',
        )
        self.assertEqual(params[11], True)
        self.assertEqual(params[12], 'position_liquidity')
        self.assertEqual(connection.commit_count, 1)
