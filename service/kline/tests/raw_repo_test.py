import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.raw_repo import RawRepository  # noqa: E402


class FakeCursor:
    def __init__(self, connection, dictionary=False):
        self.connection = connection
        self.dictionary = dictionary
        self.executed = []
        self.closed = False
        self.lastrowid = 0

    def execute(self, sql: str, params=None):
        self.executed.append((sql, params))
        if 'INSERT INTO raw_incoming_bundles' in sql:
            self.lastrowid += 1
        self.connection.last_select = (sql, params)

    def fetchone(self):
        sql, params = self.connection.last_select
        return self.connection.select_results.get((self.connection._normalize_sql(sql), params))

    def fetchall(self):
        sql, params = self.connection.last_select
        row = self.connection.select_results.get((self.connection._normalize_sql(sql), params))
        if row is None:
            return []
        if isinstance(row, list):
            return row
        return [row]

    def close(self):
        self.closed = True


class FakeConnection:
    def __init__(self):
        self.cursor_instances = []
        self.commit_count = 0
        self.rollback_count = 0
        self.started_transactions = 0
        self.select_results = {}
        self.last_select = ('', None)

    def cursor(self, **_kwargs):
        cursor = FakeCursor(self, dictionary=_kwargs.get('dictionary', False))
        self.cursor_instances.append(cursor)
        return cursor

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def start_transaction(self):
        self.started_transactions += 1

    def add_select_result(self, sql: str, params, row):
        self.select_results[(self._normalize_sql(sql), params)] = row

    def _normalize_sql(self, sql: str) -> str:
        return ' '.join(sql.split())


class RawRepositoryTest(unittest.TestCase):
    def test_ordered_schema_definitions_include_layer1_tables_in_dependency_order(self):
        repository = RawRepository(FakeConnection())

        names = [name for name, _ddl in repository.ordered_schema_definitions()]

        self.assertEqual(names, [
            'chain_cursors',
            'raw_blocks',
            'raw_incoming_bundles',
            'raw_posted_messages',
            'raw_operations',
            'raw_outgoing_messages',
            'raw_events',
            'raw_oracle_responses',
            'processing_cursors',
            'ingestion_anomalies',
            'raw_block_ingest_runs',
        ])

    def test_ensure_schema_executes_all_layer1_ddl_and_commits_once(self):
        connection = FakeConnection()
        repository = RawRepository(connection)

        repository.ensure_schema()

        self.assertEqual(
            len(connection.cursor_instances[0].executed),
            len(repository.ordered_schema_definitions()),
        )
        self.assertEqual(connection.commit_count, 1)
        self.assertTrue(connection.cursor_instances[0].closed)

    def test_ingest_block_persists_child_raw_rows_and_advances_cursor(self):
        connection = FakeConnection()
        repository = RawRepository(connection)

        result = repository.ingest_block({
            'chain_id': 'chain-a',
            'height': 7,
            'block_hash': 'hash-7',
            'timestamp_ms': 123456,
            'incoming_bundles': [
                {
                    'origin_chain_id': 'chain-b',
                    'source_cert_hash': 'cert-1',
                    'posted_messages': [
                        {
                            'message_index': 0,
                            'message_kind': 'Tracked',
                            'message_type': 'User',
                            'raw_message_bytes': b'hello',
                        },
                    ],
                },
            ],
            'operations': [
                {'operation_index': 0, 'raw_operation_bytes': b'op'},
            ],
            'outgoing_messages': [
                {'message_index': 0, 'destination_chain_id': 'chain-c', 'raw_message_bytes': b'out'},
            ],
            'events': [
                {
                    'event_index': 0,
                    'stream_id': 'stream-1',
                    'application_id': 'app-evt',
                    'stream_name': 'fills',
                    'raw_event_bytes': b'evt',
                },
            ],
            'oracle_responses': [
                {'response_index': 0, 'response_type': 'blob', 'raw_response_bytes': b'oracle'},
            ],
        })

        write_cursor = connection.cursor_instances[-1]
        executed_sql = '\n'.join(sql for sql, _params in write_cursor.executed)
        self.assertIn('INSERT INTO raw_incoming_bundles', executed_sql)
        self.assertIn('INSERT INTO raw_posted_messages', executed_sql)
        self.assertIn('INSERT INTO raw_operations', executed_sql)
        self.assertIn('INSERT INTO raw_outgoing_messages', executed_sql)
        self.assertIn('INSERT INTO raw_events', executed_sql)
        self.assertIn('INSERT INTO raw_oracle_responses', executed_sql)
        self.assertIn('INSERT INTO raw_block_ingest_runs', executed_sql)
        self.assertIn('"event_count":1', str(write_cursor.executed[-1][1]))
        self.assertIn('"oracle_response_count":1', str(write_cursor.executed[-1][1]))
        self.assertEqual(result['ingest_status'], 'ingested')
        self.assertEqual(connection.started_transactions, 1)

    def test_ingest_block_uses_canonical_bytes_when_raw_block_bytes_missing(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        block = {
            'chain_id': 'chain-a',
            'height': 7,
            'block_hash': 'hash-7',
            'timestamp_ms': 123456,
            'incoming_bundles': [],
            'operations': [],
            'outgoing_messages': [],
            'events': [],
            'oracle_responses': [],
        }

        repository.ingest_block(block)

        write_cursor = connection.cursor_instances[-1]
        raw_block_insert_params = next(
            params
            for sql, params in write_cursor.executed
            if 'INSERT INTO raw_blocks' in sql
        )
        self.assertEqual(raw_block_insert_params[13], repository.fingerprint.build_bytes(block))

    def test_record_failed_ingest_run_persists_failure_row(self):
        connection = FakeConnection()
        repository = RawRepository(connection)

        repository.record_failed_ingest_run('chain-a', 7, 'catch_up', 'rpc failed')

        cursor = connection.cursor_instances[-1]
        executed_sql = '\n'.join(sql for sql, _params in cursor.executed)
        self.assertIn('INSERT INTO raw_block_ingest_runs', executed_sql)
        self.assertEqual(
            cursor.executed[-1][1],
            ('chain-a', 7, 'catch_up', 'failed', 'rpc failed'),
        )
        self.assertEqual(connection.commit_count, 1)

    def test_list_chain_cursors_returns_rows_ordered_by_updated_at(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        connection.add_select_result(
            f'''
            SELECT
                chain_id,
                last_finalized_height,
                last_finalized_block_hash,
                last_attempted_height,
                last_attempted_at,
                last_success_at,
                sync_status,
                consecutive_failures,
                last_error,
                updated_at
            FROM chain_cursors
            WHERE chain_id IN (%s, %s)
            ORDER BY updated_at DESC, chain_id ASC
            LIMIT %s
            ''',
            ('chain-a', 'chain-b', 10),
            [
                {'chain_id': 'chain-b', 'last_finalized_height': 9},
                {'chain_id': 'chain-a', 'last_finalized_height': 8},
            ],
        )

        rows = repository.list_chain_cursors(chain_ids=('chain-a', 'chain-b'), limit=10)

        self.assertEqual(rows, [
            {'chain_id': 'chain-b', 'last_finalized_height': 9},
            {'chain_id': 'chain-a', 'last_finalized_height': 8},
        ])

    def test_list_recent_ingest_runs_filters_by_chain_and_status(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        connection.add_select_result(
            f'''
            SELECT
                run_id,
                chain_id,
                height,
                mode,
                status,
                block_hash,
                started_at,
                finished_at,
                error_text,
                summary_json
            FROM raw_block_ingest_runs
            WHERE chain_id IN (%s) AND status IN (%s, %s)
            ORDER BY started_at DESC, run_id DESC
            LIMIT %s
            ''',
            ('chain-a', 'failed', 'success', 5),
            [
                {'run_id': 2, 'chain_id': 'chain-a', 'status': 'failed'},
                {'run_id': 1, 'chain_id': 'chain-a', 'status': 'success'},
            ],
        )

        rows = repository.list_recent_ingest_runs(
            chain_ids=('chain-a',),
            statuses=('failed', 'success'),
            limit=5,
        )

        self.assertEqual(rows, [
            {'run_id': 2, 'chain_id': 'chain-a', 'status': 'failed'},
            {'run_id': 1, 'chain_id': 'chain-a', 'status': 'success'},
        ])

    def test_list_normalization_candidates_returns_operation_items(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        connection.add_select_result(
            f'''
            SELECT
                operation_id,
                chain_id,
                block_hash,
                height,
                operation_index,
                application_id,
                authenticated_owner,
                raw_operation_bytes
            FROM raw_operations
            WHERE application_id IS NOT NULL AND operation_id > %s
            ORDER BY operation_id ASC
            LIMIT %s
            ''',
            (7, 2),
            [
                {
                    'operation_id': 8,
                    'chain_id': 'chain-a',
                    'block_hash': 'block-8',
                    'height': 8,
                    'operation_index': 3,
                    'application_id': 'app-ops',
                    'authenticated_owner': 'owner-a',
                    'raw_operation_bytes': b'op',
                },
            ],
        )

        items = repository.list_normalization_candidates(
            raw_table='raw_operations',
            after_sequence=7,
            limit=2,
        )

        self.assertEqual(items, [
            {
                'raw_fact_id': '8',
                'raw_table': 'raw_operations',
                'application_id': 'app-ops',
                'payload_kind': 'operation',
                'raw_bytes': b'op',
                'chain_id': 'chain-a',
                'target_chain_id': 'chain-a',
                'block_hash': 'block-8',
                'target_block_hash': 'block-8',
                'transaction_index': 3,
                'authenticated_owner': 'owner-a',
            },
        ])

    def test_list_normalization_candidates_returns_posted_message_items_with_reject(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        connection.add_select_result(
            f'''
            SELECT
                m.posted_message_id,
                m.origin_chain_id,
                m.source_cert_hash,
                m.transaction_index,
                m.message_index,
                m.authenticated_owner,
                m.application_id,
                m.raw_message_bytes,
                b.target_chain_id,
                b.target_block_hash,
                b.action
            FROM raw_posted_messages AS m
            INNER JOIN raw_incoming_bundles AS b
                ON b.bundle_id = m.bundle_id
            WHERE m.application_id IS NOT NULL AND m.posted_message_id > %s
            ORDER BY m.posted_message_id ASC
            LIMIT %s
            ''',
            (5, 2),
            [
                {
                    'posted_message_id': 6,
                    'origin_chain_id': 'chain-user',
                    'source_cert_hash': 'cert-6',
                    'transaction_index': 4,
                    'message_index': 1,
                    'authenticated_owner': 'owner-b',
                    'application_id': 'app-msg',
                    'raw_message_bytes': b'msg',
                    'target_chain_id': 'chain-pool',
                    'target_block_hash': 'block-6',
                    'action': 'Reject',
                },
            ],
        )

        items = repository.list_normalization_candidates(
            raw_table='raw_posted_messages',
            after_sequence=5,
            limit=2,
        )

        self.assertEqual(items, [
            {
                'raw_fact_id': '6',
                'raw_table': 'raw_posted_messages',
                'application_id': 'app-msg',
                'payload_kind': 'message',
                'raw_bytes': b'msg',
                'chain_id': 'chain-pool',
                'source_chain_id': 'chain-user',
                'target_chain_id': 'chain-pool',
                'target_block_hash': 'block-6',
                'source_cert_hash': 'cert-6',
                'transaction_index': 4,
                'message_index': 1,
                'authenticated_owner': 'owner-b',
                'execution_status': 'rejected',
                'reject_reason': 'incoming bundle action Reject',
            },
        ])

    def test_list_normalization_candidates_returns_event_items(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        connection.add_select_result(
            f'''
            SELECT
                event_id,
                chain_id,
                block_hash,
                height,
                transaction_index,
                event_index,
                stream_id,
                application_id,
                stream_name,
                stream_index,
                raw_event_bytes
            FROM raw_events
            WHERE application_id IS NOT NULL AND event_id > %s
            ORDER BY event_id ASC
            LIMIT %s
            ''',
            (11, 3),
            [
                {
                    'event_id': 12,
                    'chain_id': 'chain-pool',
                    'block_hash': 'block-12',
                    'height': 42,
                    'transaction_index': 5,
                    'event_index': 2,
                    'stream_id': 'app-pool:fills',
                    'application_id': 'app-pool',
                    'stream_name': 'fills',
                    'stream_index': 9,
                    'raw_event_bytes': b'evt',
                },
            ],
        )

        items = repository.list_normalization_candidates(
            raw_table='raw_events',
            after_sequence=11,
            limit=3,
        )

        self.assertEqual(items, [
            {
                'raw_fact_id': '12',
                'raw_table': 'raw_events',
                'application_id': 'app-pool',
                'payload_kind': 'event',
                'raw_bytes': b'evt',
                'chain_id': 'chain-pool',
                'target_chain_id': 'chain-pool',
                'block_hash': 'block-12',
                'target_block_hash': 'block-12',
                'transaction_index': 5,
                'event_index': 2,
                'stream_id': 'app-pool:fills',
                'stream_name': 'fills',
                'stream_index': 9,
                'execution_status': 'observed',
            },
        ])

    def test_list_ingestion_anomalies_filters_by_status(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        connection.add_select_result(
            f'''
            SELECT
                anomaly_id,
                anomaly_type,
                severity,
                chain_id,
                height,
                block_hash,
                object_type,
                object_identity,
                expected_fingerprint,
                observed_fingerprint,
                details_json,
                first_seen_at,
                last_seen_at,
                occurrence_count,
                status
            FROM ingestion_anomalies
            WHERE status IN (%s)
            ORDER BY last_seen_at DESC, anomaly_id DESC
            LIMIT %s
            ''',
            ('open', 3),
            [
                {'anomaly_id': 5, 'status': 'open', 'anomaly_type': 'block_hash_mismatch'},
            ],
        )

        rows = repository.list_ingestion_anomalies(statuses=('open',), limit=3)

        self.assertEqual(rows, [
            {'anomaly_id': 5, 'status': 'open', 'anomaly_type': 'block_hash_mismatch'},
        ])

    def test_ingest_block_replay_safe_existing_rows_skip_duplicate_insert(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        block_hash = 'hash-7'
        connection.add_select_result(
            f'''
            SELECT block_hash
            FROM raw_blocks
            WHERE chain_id = %s AND height = %s
            ''',
            ('chain-a', 7),
            {'block_hash': block_hash},
        )
        connection.add_select_result(
            f'''
            SELECT bundle_id, origin_chain_id, action, source_height, source_timestamp_ms, source_cert_hash, transaction_index
            FROM raw_incoming_bundles
            WHERE target_block_hash = %s AND bundle_index = %s
            ''',
            (block_hash, 0),
            {
                'bundle_id': 9,
                'origin_chain_id': 'chain-b',
                'action': 'Accept',
                'source_height': 0,
                'source_timestamp_ms': 0,
                'source_cert_hash': 'cert-1',
                'transaction_index': 0,
            },
        )
        connection.add_select_result(
            f'''
            SELECT origin_chain_id, source_cert_hash, transaction_index, authenticated_owner, grant_amount, refund_grant_to, message_kind, message_type, application_id, system_message_type, system_target, system_amount, system_source, system_owner, system_recipient, raw_message_bytes
            FROM raw_posted_messages
            WHERE bundle_id = %s AND message_index = %s
            ''',
            (9, 0),
            {
                'origin_chain_id': 'chain-b',
                'source_cert_hash': 'cert-1',
                'transaction_index': 0,
                'authenticated_owner': None,
                'grant_amount': None,
                'refund_grant_to': None,
                'message_kind': 'Tracked',
                'message_type': 'User',
                'application_id': None,
                'system_message_type': None,
                'system_target': None,
                'system_amount': None,
                'system_source': None,
                'system_owner': None,
                'system_recipient': None,
                'raw_message_bytes': b'hello',
            },
        )

        repository.ingest_block({
            'chain_id': 'chain-a',
            'height': 7,
            'block_hash': block_hash,
            'timestamp_ms': 123456,
            'incoming_bundles': [
                {
                    'origin_chain_id': 'chain-b',
                    'source_cert_hash': 'cert-1',
                    'posted_messages': [
                        {
                            'message_index': 0,
                            'message_kind': 'Tracked',
                            'message_type': 'User',
                            'raw_message_bytes': b'hello',
                        },
                    ],
                },
            ],
        })

        write_cursor = connection.cursor_instances[-1]
        executed_sql = '\n'.join(sql for sql, _params in write_cursor.executed)
        self.assertNotIn('INSERT INTO raw_blocks', executed_sql)
        self.assertNotIn('INSERT INTO raw_incoming_bundles', executed_sql)
        self.assertNotIn('INSERT INTO raw_posted_messages', executed_sql)

    def test_ingest_block_conflict_rolls_back_and_records_anomaly(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        connection.add_select_result(
            f'''
            SELECT block_hash
            FROM raw_blocks
            WHERE chain_id = %s AND height = %s
            ''',
            ('chain-a', 7),
            {'block_hash': 'other-hash'},
        )

        with self.assertRaisesRegex(ValueError, 'Conflicting block hash'):
            repository.ingest_block({
                'chain_id': 'chain-a',
                'height': 7,
                'block_hash': 'hash-7',
                'timestamp_ms': 123456,
            })

        self.assertEqual(connection.rollback_count, 1)
        anomaly_sql = '\n'.join(
            sql
            for cursor in connection.cursor_instances
            for sql, _params in cursor.executed
        )
        self.assertIn('INSERT INTO ingestion_anomalies', anomaly_sql)
        anomaly_params = next(
            params
            for cursor in connection.cursor_instances
            for sql, params in cursor.executed
            if 'INSERT INTO ingestion_anomalies' in sql
        )
        self.assertEqual(
            anomaly_params[9],
            repository.fingerprint.build_json({
                'chain_id': 'chain-a',
                'height': 7,
                'block_hash': 'hash-7',
                'timestamp_ms': 123456,
            }),
        )

    def test_ingest_block_child_conflict_records_anomaly(self):
        connection = FakeConnection()
        repository = RawRepository(connection)
        block_hash = 'hash-7'
        connection.add_select_result(
            f'''
            SELECT block_hash
            FROM raw_blocks
            WHERE chain_id = %s AND height = %s
            ''',
            ('chain-a', 7),
            {'block_hash': block_hash},
        )
        connection.add_select_result(
            f'''
            SELECT bundle_id, origin_chain_id, action, source_height, source_timestamp_ms, source_cert_hash, transaction_index
            FROM raw_incoming_bundles
            WHERE target_block_hash = %s AND bundle_index = %s
            ''',
            (block_hash, 0),
            {
                'bundle_id': 9,
                'origin_chain_id': 'chain-b',
                'action': 'Accept',
                'source_height': 0,
                'source_timestamp_ms': 0,
                'source_cert_hash': 'cert-1',
                'transaction_index': 0,
            },
        )
        connection.add_select_result(
            f'''
            SELECT origin_chain_id, source_cert_hash, transaction_index, authenticated_owner, grant_amount, refund_grant_to, message_kind, message_type, application_id, system_message_type, system_target, system_amount, system_source, system_owner, system_recipient, raw_message_bytes
            FROM raw_posted_messages
            WHERE bundle_id = %s AND message_index = %s
            ''',
            (9, 0),
            {
                'origin_chain_id': 'chain-b',
                'source_cert_hash': 'cert-1',
                'transaction_index': 0,
                'authenticated_owner': None,
                'grant_amount': None,
                'refund_grant_to': None,
                'message_kind': 'Tracked',
                'message_type': 'User',
                'application_id': None,
                'system_message_type': None,
                'system_target': None,
                'system_amount': None,
                'system_source': None,
                'system_owner': None,
                'system_recipient': None,
                'raw_message_bytes': b'hello',
            },
        )

        with self.assertRaisesRegex(ValueError, 'Conflicting posted message'):
            repository.ingest_block({
                'chain_id': 'chain-a',
                'height': 7,
                'block_hash': block_hash,
                'timestamp_ms': 123456,
                'incoming_bundles': [
                    {
                        'origin_chain_id': 'chain-b',
                        'source_cert_hash': 'cert-1',
                        'posted_messages': [
                            {
                                'message_index': 0,
                                'message_kind': 'Tracked',
                                'message_type': 'User',
                                'raw_message_bytes': b'world',
                            },
                        ],
                    },
                ],
            })

        anomaly_params = next(
            params
            for cursor in connection.cursor_instances
            for sql, params in cursor.executed
            if 'INSERT INTO ingestion_anomalies' in sql
        )
        self.assertEqual(anomaly_params[0], 'posted_message_mismatch')
        self.assertEqual(anomaly_params[5], 'raw_posted_message')
