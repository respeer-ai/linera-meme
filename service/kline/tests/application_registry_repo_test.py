import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.application_registry_repo import ApplicationRegistryRepository  # noqa: E402


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


class ApplicationRegistryRepositoryTest(unittest.TestCase):
    def test_ensure_schema_creates_application_registry_table(self):
        connection = FakeConnection()
        repository = ApplicationRegistryRepository(connection)

        repository.ensure_schema()

        self.assertIn('CREATE TABLE IF NOT EXISTS application_registry', connection.cursor_instances[0].executed[0][0])
        self.assertEqual(connection.commit_count, 1)

    def test_upsert_application_persists_json_metadata(self):
        connection = FakeConnection()
        repository = ApplicationRegistryRepository(connection)

        repository.upsert_application({
            'application_id': 'app-1',
            'app_type': 'pool',
            'chain_id': 'chain-a',
            'discovered_from': 'manual',
            'status': 'active',
            'metadata_json': {'b': 2, 'a': 1},
        })

        params = connection.cursor_instances[-1].executed[-1][1]
        self.assertEqual(params[0], 'app-1')
        self.assertEqual(params[1], 'pool')
        self.assertEqual(params[9], '{"a":1,"b":2}')

    def test_get_application_returns_row(self):
        connection = FakeConnection()
        repository = ApplicationRegistryRepository(connection)
        connection.add_select_result(
            '''
            SELECT
                application_id,
                app_type,
                chain_id,
                creator_chain_id,
                owner,
                parent_application_id,
                abi_version,
                discovered_from,
                status,
                metadata_json
            FROM application_registry
            WHERE application_id = %s
            ''',
            ('app-1',),
            {'application_id': 'app-1', 'app_type': 'pool'},
        )

        self.assertEqual(
            repository.get_application('app-1'),
            {'application_id': 'app-1', 'app_type': 'pool'},
        )
