import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.projection_pool_catalog_repo import ProjectionPoolCatalogRepository  # noqa: E402


class ProjectionPoolCatalogRepositoryTest(unittest.TestCase):
    def test_list_current_pools_joins_catalog_with_pool_state_projection(self):
        class FakePoolCatalogProjectionRepository:
            def list_pool_catalog(self):
                return [
                    {
                        'pool_id': 7,
                        'pool_application': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'token_0': 'AAA',
                        'token_1': 'BBB',
                    },
                    {
                        'pool_id': 8,
                        'pool_application': '0x2222222222222222222222222222222222222222222222222222222222222222@chain-b',
                        'token_0': 'CCC',
                        'token_1': 'TLINERA',
                    },
                ]

        class FakePoolStateProjectionRepository:
            def list_pool_state_snapshots(self):
                return [
                    {
                        'pool_application_id': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'live_reserve_0': '10',
                        'live_reserve_1': '20',
                        'live_total_supply': '30',
                        'live_k_last': '40',
                        'last_trade_time_ms': 1000,
                        'last_liquidity_event_time_ms': 900,
                        'state_payload_json': {'virtual_initial_liquidity': False},
                    }
                ]

        repository = ProjectionPoolCatalogRepository(
            pool_catalog_projection_repository=FakePoolCatalogProjectionRepository(),
            pool_state_projection_repository=FakePoolStateProjectionRepository(),
        )

        pools = repository.list_current_pools()

        self.assertEqual(
            pools,
            [
                {
                    'pool_id': 7,
                    'pool_application': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'live_reserve_0': '10',
                    'live_reserve_1': '20',
                    'live_total_supply': '30',
                    'live_k_last': '40',
                    'last_trade_time_ms': 1000,
                    'last_liquidity_event_time_ms': 900,
                    'state_payload_json': {'virtual_initial_liquidity': False},
                },
                {
                    'pool_id': 8,
                    'pool_application': '0x2222222222222222222222222222222222222222222222222222222222222222@chain-b',
                    'token_0': 'CCC',
                    'token_1': 'TLINERA',
                    'live_reserve_0': None,
                    'live_reserve_1': None,
                    'live_total_supply': None,
                    'live_k_last': None,
                    'last_trade_time_ms': None,
                    'last_liquidity_event_time_ms': None,
                    'state_payload_json': None,
                },
            ],
        )

    def test_list_current_pools_prefers_projection_pool_created_metadata_for_tokens(self):
        class FakePoolCatalogProjectionRepository:
            def list_pool_catalog(self):
                return [
                    {
                        'pool_id': 7,
                        'pool_application': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'token_0': 'LEGACY-A',
                        'token_1': 'LEGACY-B',
                    }
                ]

        class FakePoolStateProjectionRepository:
            def list_pool_state_snapshots(self):
                return [
                    {
                        'pool_application_id': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'live_reserve_0': '10',
                        'live_reserve_1': '20',
                        'live_total_supply': '30',
                        'live_k_last': '40',
                        'last_trade_time_ms': 1000,
                        'last_liquidity_event_time_ms': 900,
                        'state_payload_json': {
                            'pool_created_metadata': {
                                'token_0': 'AAA',
                                'token_1': 'TLINERA',
                            },
                        },
                    }
                ]

        repository = ProjectionPoolCatalogRepository(
            pool_catalog_projection_repository=FakePoolCatalogProjectionRepository(),
            pool_state_projection_repository=FakePoolStateProjectionRepository(),
        )

        pools = repository.list_current_pools()

        self.assertEqual(pools[0]['token_0'], 'AAA')
        self.assertEqual(pools[0]['token_1'], 'TLINERA')

    def test_list_current_pools_ignores_legacy_colon_pool_state_key(self):
        class FakePoolCatalogProjectionRepository:
            def list_pool_catalog(self):
                return [
                    {
                        'pool_id': 7,
                        'pool_application': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'token_0': 'AAA',
                        'token_1': 'BBB',
                    }
                ]

        class FakePoolStateProjectionRepository:
            def list_pool_state_snapshots(self):
                return [
                    {
                        'pool_application_id': 'chain-a:0x1111111111111111111111111111111111111111111111111111111111111111',
                        'pool_chain_id': 'chain-a',
                        'live_reserve_0': '10',
                        'live_reserve_1': '20',
                        'live_total_supply': '30',
                        'live_k_last': '40',
                        'last_trade_time_ms': 1000,
                        'last_liquidity_event_time_ms': 900,
                        'state_payload_json': {},
                    }
                ]

        repository = ProjectionPoolCatalogRepository(
            pool_catalog_projection_repository=FakePoolCatalogProjectionRepository(),
            pool_state_projection_repository=FakePoolStateProjectionRepository(),
        )

        pools = repository.list_current_pools()

        self.assertEqual(len(pools), 1)
        self.assertEqual(pools[0]['pool_application'], '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a')
        self.assertIsNone(pools[0]['live_reserve_0'])

    def test_list_current_pool_views_builds_compat_objects(self):
        class FakePoolCatalogProjectionRepository:
            def list_pool_catalog(self):
                return [
                    {
                        'pool_id': 7,
                        'pool_application': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'token_0': 'AAA',
                        'token_1': 'BBB',
                    }
                ]

        class FakePoolStateProjectionRepository:
            def list_pool_state_snapshots(self):
                return [
                    {
                        'pool_application_id': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'live_reserve_0': '10',
                        'live_reserve_1': '20',
                        'live_total_supply': '30',
                        'live_k_last': '40',
                        'last_trade_time_ms': 1000,
                        'last_liquidity_event_time_ms': 900,
                        'state_payload_json': {},
                    }
                ]

        repository = ProjectionPoolCatalogRepository(
            pool_catalog_projection_repository=FakePoolCatalogProjectionRepository(),
            pool_state_projection_repository=FakePoolStateProjectionRepository(),
        )

        pools = repository.list_current_pool_views()

        self.assertEqual(len(pools), 1)
        self.assertEqual(pools[0].pool_id, 7)
        self.assertEqual(pools[0].pool_application.chain_id, 'chain-a')
        self.assertEqual(pools[0].pool_application.owner, '0x1111111111111111111111111111111111111111111111111111111111111111')


if __name__ == '__main__':
    unittest.main()
