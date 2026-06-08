import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.pool_fee_to_history_projection_repo import PoolFeeToHistoryProjectionRepository  # noqa: E402


class PoolFeeToHistoryProjectionRepositoryTest(unittest.TestCase):
    class FakeCursor:
        def __init__(self):
            self.executed = []
            self.rows = []

        def execute(self, sql, params=()):
            self.executed.append((sql, params))

        def fetchall(self):
            return self.rows

        def close(self):
            return None

    class FakeConnection:
        def __init__(self):
            self.cursor_obj = PoolFeeToHistoryProjectionRepositoryTest.FakeCursor()
            self.commits = 0

        def cursor(self, dictionary=False):
            self.dictionary = dictionary
            return self.cursor_obj

        def commit(self):
            self.commits += 1

    def test_ensure_schema_skips_width_migration_when_columns_already_match(self):
        class FakeCursor:
            def __init__(self):
                self.executed = []

            def execute(self, sql, params=()):
                self.executed.append((" ".join(sql.split()), params))

            def fetchone(self):
                column_name = self.executed[-1][1][0]
                return {
                    'pool_fee_to_history_id': {'Type': 'varchar(512)'},
                    'pool_application': {'Type': 'varchar(256)'},
                    'pool_application_id': {'Type': 'varchar(256)'},
                    'source_event_key': {'Type': 'varchar(255)'},
                }[column_name]

            def close(self):
                return None

        class FakeConnection:
            def __init__(self):
                self.cursor_obj = FakeCursor()
                self.commits = 0

            def cursor(self, dictionary=False):
                return self.cursor_obj

            def commit(self):
                self.commits += 1

        connection = FakeConnection()
        repo = PoolFeeToHistoryProjectionRepository(connection)

        repo.ensure_schema()

        executed_sql = [sql for sql, _params in connection.cursor_obj.executed]
        self.assertEqual(sum(1 for sql in executed_sql if sql.startswith('ALTER TABLE')), 0)
        self.assertEqual(connection.commits, 1)

    def test_materialize_events_records_pool_created_creator_as_initial_fee_to(self):
        connection = self.FakeConnection()
        repo = PoolFeeToHistoryProjectionRepository(connection)

        count = repo.materialize_events([self._pool_created_event()])

        self.assertEqual(count, 1)
        self.assertEqual(connection.commits, 1)
        params = connection.cursor_obj.executed[0][1]
        self.assertEqual(params[1], '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-pool')
        self.assertEqual(params[4], 0)
        self.assertEqual(params[5], 0)
        self.assertEqual(params[6], '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-owner')
        self.assertEqual(params[7], 'swap_pool_created_recorded')

    def test_materialize_events_uses_public_pool_application_from_set_fee_to_event(self):
        connection = self.FakeConnection()
        repo = PoolFeeToHistoryProjectionRepository(connection)
        event = self._set_fee_to_event()
        event['application_id'] = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-pool'
        event['source_chain_id'] = 'ignored-chain'

        count = repo.materialize_events([event])

        self.assertEqual(count, 1)
        params = connection.cursor_obj.executed[0][1]
        self.assertEqual(params[1], '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-pool')
        self.assertEqual(params[3], 'chain-pool')

    def test_materialize_events_records_set_fee_to_change(self):
        connection = self.FakeConnection()
        repo = PoolFeeToHistoryProjectionRepository(connection)

        count = repo.materialize_events([self._set_fee_to_event()])

        self.assertEqual(count, 1)
        params = connection.cursor_obj.executed[0][1]
        self.assertEqual(params[1], '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-pool')
        self.assertEqual(params[4], 42)
        self.assertEqual(params[5], 987654)
        self.assertEqual(params[6], '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc@chain-owner')
        self.assertEqual(params[7], 'pool_set_fee_to_message_observed')

    def test_materialize_events_ignores_rejected_events(self):
        class NoCursorConnection:
            def cursor(self, dictionary=False):
                raise AssertionError('cursor should not be used when no rows exist')

        repo = PoolFeeToHistoryProjectionRepository(NoCursorConnection())
        event = self._pool_created_event()
        event['normalization_status'] = 'rejected'

        self.assertEqual(repo.materialize_events([event]), 0)

    def test_list_pool_fee_to_history_returns_projection_rows_in_read_model_shape(self):
        connection = self.FakeConnection()
        connection.cursor_obj.rows = [{
            'transaction_id': 42,
            'event_time_ms': 987654,
            'fee_to_account': '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc@chain-owner',
            'event_family': 'pool_set_fee_to_message_observed',
            'source_event_key': 'event-2',
        }]
        repo = PoolFeeToHistoryProjectionRepository(connection)

        rows = repo.list_pool_fee_to_history(
            pool_application_id='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-pool',
        )

        self.assertEqual(rows, [{
            'transaction_id': 42,
            'created_at': 987654,
            'fee_to_account': '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc@chain-owner',
            'event_family': 'pool_set_fee_to_message_observed',
            'source_event_key': 'event-2',
        }])

    def _pool_created_event(self):
        return {
            'normalized_event_id': 'event-1',
            'event_family': 'swap_pool_created_recorded',
            'normalization_status': 'observed',
            'event_payload_json': {
                'decoded_payload_json': {
                    'pool_application': {
                        'chain_id': 'chain-pool',
                        'owner': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                    },
                    'creator': {
                        'chain_id': 'chain-owner',
                        'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                    },
                },
            },
        }

    def _set_fee_to_event(self):
        return {
            'normalized_event_id': 'event-2',
            'event_family': 'pool_set_fee_to_message_observed',
            'normalization_status': 'observed',
            'application_id': 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
            'source_chain_id': 'chain-pool',
            'event_payload_json': {
                'decoded_payload_json': {
                    'transaction_id': 42,
                    'created_at_micros': 987654321,
                    'new_fee_to': {
                        'chain_id': 'chain-owner',
                        'owner': '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc',
                    },
                },
            },
        }


if __name__ == '__main__':
    unittest.main()
