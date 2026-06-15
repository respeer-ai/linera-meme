import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.pool_registry_metadata_repo import PoolRegistryMetadataRepository  # noqa: E402


class PoolRegistryMetadataRepositoryTest(unittest.TestCase):
    def test_list_pool_metadata_filters_to_latest_static_config_swap_parent(self):
        class FakeConnection:
            def __init__(self):
                self.cursor_obj = FakeCursor()

            def cursor(self, **_kwargs):
                return self.cursor_obj

        class FakeCursor:
            def __init__(self):
                self.executed = []

            def execute(self, sql, params=()):
                self.executed.append((sql, params))

            def fetchall(self):
                return [
                    {
                        'application_id': '1111111111111111111111111111111111111111111111111111111111111111',
                        'chain_id': 'chain-a',
                        'metadata_json': {
                            'pool_id': 1000,
                            'token_0': 'AAA',
                            'token_1': None,
                        },
                    }
                ]

            def close(self):
                return None

        connection = FakeConnection()
        repository = PoolRegistryMetadataRepository(connection)

        rows = repository.list_pool_metadata()

        self.assertEqual(len(rows), 1)
        sql = connection.cursor_obj.executed[0][0]
        self.assertIn("current_swap.app_type = 'swap'", sql)
        self.assertIn("current_swap.discovered_from = 'static_config'", sql)
        self.assertIn('pool_app.parent_application_id = current_swap.application_id', sql)


if __name__ == '__main__':
    unittest.main()
