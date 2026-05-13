import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.processing_cursor_repo import ProcessingCursorRepository  # noqa: E402


class FakeCursor:
    def __init__(self, connection, dictionary=False):
        self.connection = connection
        self.dictionary = dictionary
        self.executed = []
        self.closed = False

    def execute(self, sql: str, params=None):
        self.executed.append((sql, params))
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
        self.select_results = {}
        self.last_select = ('', None)

    def cursor(self, **kwargs):
        cursor = FakeCursor(self, dictionary=kwargs.get('dictionary', False))
        self.cursor_instances.append(cursor)
        return cursor

    def commit(self):
        self.commit_count += 1

    def add_select_result(self, sql: str, params, row):
        self.select_results[(self._normalize_sql(sql), params)] = row

    def _normalize_sql(self, sql: str) -> str:
        return ' '.join(sql.split())


class ProcessingCursorRepositoryTest(unittest.TestCase):
    def test_load_cursor_returns_row(self):
        connection = FakeConnection()
        repository = ProcessingCursorRepository(connection)
        connection.add_select_result(
            '''
            SELECT
                cursor_name,
                cursor_scope,
                partition_key,
                last_sequence,
                last_block_hash,
                last_success_at,
                last_attempt_at,
                status,
                consecutive_failures,
                last_error,
                updated_at
            FROM processing_cursors
            WHERE cursor_name = %s AND partition_key = %s
            ''',
            ('layer2_normalizer', 'global'),
            {'cursor_name': 'layer2_normalizer', 'partition_key': 'global', 'status': 'ready'},
        )

        row = repository.load_cursor(
            cursor_name='layer2_normalizer',
            partition_key='global',
        )

        self.assertEqual(row['status'], 'ready')

    def test_list_cursors_filters_by_scope(self):
        connection = FakeConnection()
        repository = ProcessingCursorRepository(connection)
        connection.add_select_result(
            '''
            SELECT
                cursor_name,
                cursor_scope,
                partition_key,
                last_sequence,
                last_block_hash,
                last_success_at,
                last_attempt_at,
                status,
                consecutive_failures,
                last_error,
                updated_at
            FROM processing_cursors
            WHERE cursor_scope = %s
            ORDER BY updated_at DESC, cursor_name ASC, partition_key ASC
            LIMIT %s
            ''',
            ('normalize', 10),
            [{'cursor_name': 'layer2_normalizer', 'cursor_scope': 'normalize'}],
        )

        rows = repository.list_cursors(cursor_scope='normalize', limit=10)

        self.assertEqual(rows, [{'cursor_name': 'layer2_normalizer', 'cursor_scope': 'normalize'}])

    def test_mark_attempt_success_and_failure_commit(self):
        connection = FakeConnection()
        repository = ProcessingCursorRepository(connection)

        repository.mark_attempt(
            cursor_name='layer2_normalizer',
            cursor_scope='normalize',
            partition_key='global',
            last_sequence='raw-1',
            last_block_hash='block-1',
        )
        repository.mark_success(
            cursor_name='layer2_normalizer',
            cursor_scope='normalize',
            partition_key='global',
            last_sequence='raw-1',
            last_block_hash='block-1',
        )
        repository.mark_failure(
            cursor_name='layer2_normalizer',
            cursor_scope='normalize',
            partition_key='global',
            last_sequence='raw-1',
            last_block_hash='block-1',
            error_text='failed',
        )

        executed_sql = '\n'.join(
            sql
            for cursor in connection.cursor_instances
            for sql, _params in cursor.executed
        )
        self.assertIn('INSERT INTO processing_cursors', executed_sql)
        self.assertEqual(connection.commit_count, 3)

