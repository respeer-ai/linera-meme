import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.normalized_repo import NormalizedEventRepository  # noqa: E402


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.executed = []
        self.closed = False
        self.fetchall_result = []

    def execute(self, sql: str, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return list(self.fetchall_result)

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


class NormalizedEventRepositoryTest(unittest.TestCase):
    def test_ensure_schema_creates_normalized_events_table(self):
        connection = FakeConnection()
        repository = NormalizedEventRepository(connection)

        repository.ensure_schema()

        executed_statements = [sql for sql, _params in connection.cursor_instances[0].executed]
        self.assertIn('CREATE TABLE IF NOT EXISTS normalized_events', executed_statements[0])
        self.assertIn('reprocess_reason VARCHAR(255) NULL', executed_statements[0])
        self.assertIn('ALTER TABLE normalized_events', executed_statements[1])
        self.assertIn('MODIFY COLUMN reprocess_reason VARCHAR(255) NULL', executed_statements[1])
        self.assertEqual(connection.commit_count, 1)
        self.assertTrue(connection.cursor_instances[0].closed)

    def test_upsert_normalized_events_persists_canonical_payload_json(self):
        connection = FakeConnection()
        repository = NormalizedEventRepository(connection)

        count = repository.upsert_normalized_events(
            [
                {
                    'normalized_event_id': 'event-1',
                    'raw_fact_id': 'raw-1',
                    'raw_table': 'raw_operations',
                    'application_id': 'app-ams',
                    'payload_kind': 'operation',
                    'event_family': 'application_operation_observed',
                    'event_type': 'add_application_type',
                    'correlation_key': 'ams:chain-a:cert-1:1:application_operation_observed',
                    'normalization_status': 'observed',
                    'source_chain_id': 'chain-a',
                    'target_chain_id': 'chain-a',
                    'source_block_hash': None,
                    'target_block_hash': 'block-1',
                    'source_cert_hash': 'cert-1',
                    'transaction_index': 1,
                    'message_index': None,
                    'app_type': 'ams',
                    'payload_type': 'add_application_type',
                    'decode_status': 'decoded',
                    'event_payload_json': {
                        'decoded_payload_json': {'application_type': 'DeFi'},
                        'raw_context': {'chain_id': 'chain-a'},
                    },
                    'reprocess_reason': 'decoder_upgraded',
                },
            ]
        )

        self.assertEqual(count, 1)
        executed_sql, params = connection.cursor_instances[0].executed[0]
        self.assertIn('INSERT INTO normalized_events', executed_sql)
        self.assertEqual(
            params[19],
            '{"decoded_payload_json":{"application_type":"DeFi"},"raw_context":{"chain_id":"chain-a"}}',
        )
        self.assertEqual(connection.commit_count, 1)
        self.assertTrue(connection.cursor_instances[0].closed)

    def test_list_market_derivation_candidates_decodes_json_payload(self):
        connection = FakeConnection()
        repository = NormalizedEventRepository(connection)
        cursor = FakeCursor(connection)
        cursor.fetchall_result = [
            {
                'normalized_event_id': 'event-1',
                'raw_fact_id': '12',
                'raw_table': 'raw_posted_messages',
                'application_id': 'pool-app',
                'payload_kind': 'message',
                'event_family': 'pool_new_transaction_recorded',
                'event_type': 'new_transaction',
                'correlation_key': 'pool:key',
                'normalization_status': 'observed',
                'source_chain_id': 'source',
                'target_chain_id': 'target',
                'source_block_hash': None,
                'target_block_hash': 'block-1',
                'source_cert_hash': 'cert-1',
                'transaction_index': 7,
                'message_index': 1,
                'app_type': 'pool',
                'payload_type': 'new_transaction',
                'decode_status': 'decoded',
                'event_payload_json': '{"decoded_payload_json":{"transaction":{"transaction_type":"BuyToken0"}}}',
                'reprocess_reason': None,
            }
        ]
        connection.cursor_instances.append(cursor)
        connection.cursor = lambda **_kwargs: connection.cursor_instances.pop(0)

        rows = repository.list_market_derivation_candidates(
            raw_table='raw_posted_messages',
            after_sequence=10,
            limit=5,
        )

        self.assertEqual(rows[0]['event_payload_json']['decoded_payload_json']['transaction']['transaction_type'], 'BuyToken0')

    def test_list_market_derivation_candidates_filters_to_pool_new_transaction_family(self):
        connection = FakeConnection()
        repository = NormalizedEventRepository(connection)
        cursor = FakeCursor(connection)
        connection.cursor_instances.append(cursor)
        connection.cursor = lambda **_kwargs: connection.cursor_instances.pop(0)

        repository.list_market_derivation_candidates(
            raw_table='raw_posted_messages',
            after_sequence=10,
            limit=5,
        )

        executed_sql, params = cursor.executed[0]
        self.assertIn('raw_table = %s', executed_sql)
        self.assertIn('event_family IN (%s)', executed_sql)
        self.assertIn('normalization_status = %s', executed_sql)
        self.assertEqual(
            params,
            (
                'raw_posted_messages',
                'pool_new_transaction_recorded',
                'observed',
                10,
                5,
            ),
        )
