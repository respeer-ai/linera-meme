import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.pool_metadata_projection_resolver import PoolMetadataProjectionResolver  # noqa: E402


class PoolMetadataProjectionResolverTest(unittest.TestCase):
    def test_registry_metadata_adds_pool_missing_from_catalog(self):
        class FakePoolCatalogProjectionRepository:
            def list_pool_catalog(self):
                return []

        class FakePoolStateProjectionRepository:
            def list_pool_state_snapshots(self):
                return []

        class FakePoolRegistryMetadataRepository:
            def list_pool_metadata(self):
                return [
                    {
                        'pool_id': 1001,
                        'pool_application': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'pool_chain_id': 'chain-a',
                        'token_0': 'AAA',
                        'token_1': 'TLINERA',
                    }
                ]

        resolver = PoolMetadataProjectionResolver(
            pool_catalog_projection_repository=FakePoolCatalogProjectionRepository(),
            pool_state_projection_repository=FakePoolStateProjectionRepository(),
            pool_registry_metadata_repository=FakePoolRegistryMetadataRepository(),
        )

        metadata = resolver.metadata_for_pool_application(
            '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a'
        )

        self.assertEqual(metadata['pool_id'], 1001)
        self.assertEqual(metadata['token_0'], 'AAA')
        self.assertEqual(metadata['token_1'], 'TLINERA')

    def test_registry_metadata_overrides_catalog_local_pool_id(self):
        class FakePoolCatalogProjectionRepository:
            def list_pool_catalog(self):
                return [
                    {
                        'pool_id': 35,
                        'pool_application': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'token_0': 'AAA',
                        'token_1': 'TLINERA',
                        'creator_account': 'creator-a',
                    }
                ]

        class FakePoolStateProjectionRepository:
            def list_pool_state_snapshots(self):
                return []

        class FakePoolRegistryMetadataRepository:
            def list_pool_metadata(self):
                return [
                    {
                        'pool_id': 1001,
                        'pool_application': '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a',
                        'pool_chain_id': 'chain-a',
                        'token_0': 'AAA',
                        'token_1': 'TLINERA',
                    }
                ]

        resolver = PoolMetadataProjectionResolver(
            pool_catalog_projection_repository=FakePoolCatalogProjectionRepository(),
            pool_state_projection_repository=FakePoolStateProjectionRepository(),
            pool_registry_metadata_repository=FakePoolRegistryMetadataRepository(),
        )

        metadata = resolver.metadata_for_pool_application(
            '0x1111111111111111111111111111111111111111111111111111111111111111@chain-a'
        )

        self.assertEqual(metadata['pool_id'], 1001)
        self.assertEqual(metadata['creator_account'], 'creator-a')


if __name__ == '__main__':
    unittest.main()
