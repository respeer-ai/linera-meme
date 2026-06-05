import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.pool_catalog_projection_repo import PoolCatalogProjectionRepository  # noqa: E402


class PoolCatalogProjectionRepositoryTest(unittest.TestCase):
    def test_materialize_events_builds_catalog_rows_from_pool_created_events(self):
        class FakeCursor:
            def __init__(self):
                self.executed = []

            def execute(self, sql, params=()):
                self.executed.append((sql, params))

            def fetchone(self):
                return None

            def close(self):
                return None

        class FakeConnection:
            def __init__(self):
                self.cursor_obj = FakeCursor()
                self.commits = 0

            def cursor(self, dictionary=False):
                self.dictionary = dictionary
                return self.cursor_obj

            def commit(self):
                self.commits += 1

        connection = FakeConnection()
        repo = PoolCatalogProjectionRepository(connection)

        count = repo.materialize_events([
            {
                'normalized_event_id': 'event-1',
                'event_family': 'swap_pool_created_recorded',
                'normalization_status': 'observed',
                'event_payload_json': {
                    'decoded_payload_json': {
                        'pool_application': {
                            'chain_id': 'chain-a',
                            'owner': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                        },
                        'token_0': 'AAA',
                        'token_1': None,
                        'creator': {
                            'chain_id': 'chain-owner',
                            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                        },
                    },
                },
            }
        ])

        self.assertEqual(count, 1)
        self.assertEqual(connection.commits, 1)
        self.assertEqual(
            connection.cursor_obj.executed[0][1],
            (
                '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a',
                'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                'chain-a',
                'AAA',
                'TLINERA',
                '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-owner',
                'swap_pool_created_recorded',
                'event-1',
            ),
        )

    def test_materialize_events_ignores_rejected_and_non_pool_created_events(self):
        class FakeConnection:
            def cursor(self, dictionary=False):
                raise AssertionError('cursor should not be used when no catalog rows exist')

        repo = PoolCatalogProjectionRepository(FakeConnection())

        self.assertEqual(
            repo.materialize_events([
                {
                    'normalized_event_id': 'event-1',
                    'event_family': 'swap_pool_created_recorded',
                    'normalization_status': 'rejected',
                    'event_payload_json': {},
                },
                {
                    'normalized_event_id': 'event-2',
                    'event_family': 'pool_new_transaction_recorded',
                    'normalization_status': 'observed',
                    'event_payload_json': {},
                },
            ]),
            0,
        )

    def test_materialize_events_rejects_legacy_colon_pool_application_accounts(self):
        class FakeConnection:
            def cursor(self, dictionary=False):
                raise AssertionError('cursor should not be used for invalid account payloads')

        repo = PoolCatalogProjectionRepository(FakeConnection())

        self.assertEqual(
            repo.materialize_events([
                {
                    'normalized_event_id': 'event-legacy-account',
                    'event_family': 'swap_pool_created_recorded',
                    'normalization_status': 'observed',
                    'event_payload_json': {
                        'decoded_payload_json': {
                            'pool_application': 'chain-a:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                            'token_0': 'AAA',
                            'token_1': 'TLINERA',
                        },
                    },
                },
            ]),
            0,
        )


    def test_list_pool_catalog_filters_to_latest_static_swap_lineage(self):
        class FakeCursor:
            def __init__(self):
                self.executed = []

            def execute(self, sql, params=()):
                self.executed.append((sql, params))

            def fetchall(self):
                return []

            def close(self):
                return None

        class FakeConnection:
            def __init__(self):
                self.cursor_obj = FakeCursor()

            def cursor(self, dictionary=False):
                self.dictionary = dictionary
                return self.cursor_obj

        connection = FakeConnection()
        repo = PoolCatalogProjectionRepository(connection)

        self.assertEqual(repo.list_pool_catalog(), [])

        sql = connection.cursor_obj.executed[0][0]
        normalized_sql = " ".join(sql.split())
        self.assertIn("FROM pool_catalog_v2 pc", normalized_sql)
        self.assertIn("LEFT JOIN application_registry pool_app", normalized_sql)
        self.assertIn("pool_app.application_id = pc.pool_application_id", normalized_sql)
        self.assertIn("pool_app.app_type = 'pool'", normalized_sql)
        self.assertIn("LEFT JOIN ( SELECT current_swap.application_id", normalized_sql)
        self.assertIn("current_swap.app_type = 'swap'", normalized_sql)
        self.assertIn("current_swap.discovered_from = 'static_config'", normalized_sql)
        self.assertIn("current_swap.status = 'active'", normalized_sql)
        self.assertIn("WHERE current_swap.application_id IS NULL OR pool_app.parent_application_id = current_swap.application_id", normalized_sql)


if __name__ == '__main__':
    unittest.main()
