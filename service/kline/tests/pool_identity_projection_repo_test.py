import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.pool_identity_projection_repo import PoolIdentityProjectionRepository  # noqa: E402


class PoolIdentityProjectionRepositoryTest(unittest.TestCase):
    class FakeDb:
        def __init__(self):
            self.calls = []

        def ensure_fresh_read_connection(self):
            self.calls.append('ensure_fresh_read_connection')

    class FakeProjectionPoolCatalogRepository:
        def __init__(self, pools):
            self.pools = pools
            self.calls = []

        def list_current_pools(self):
            self.calls.append('list_current_pools')
            return list(self.pools)

    def repository(self, pools):
        catalog = self.FakeProjectionPoolCatalogRepository(pools)
        return PoolIdentityProjectionRepository(
            self.FakeDb(),
            projection_pool_catalog_repository=catalog,
        )

    def test_resolve_for_tokens_prefers_forward_match(self):
        repository = self.repository([{
            'pool_id': 7,
            'pool_application': 'chain-a:pool-app',
            'token_0': 'AAA',
            'token_1': 'BBB',
        }])

        resolved = repository.resolve_for_tokens('AAA', 'BBB')

        self.assertEqual(resolved, (7, 'chain-a:pool-app', 'AAA', 'BBB', False))

    def test_resolve_for_tokens_uses_reverse_match_when_needed(self):
        repository = self.repository([
            {
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'BBB',
                'token_1': 'AAA',
            },
        ])

        resolved = repository.resolve_for_tokens('AAA', 'BBB')

        self.assertEqual(resolved, (7, 'chain-a:pool-app', 'AAA', 'BBB', True))

    def test_resolve_for_read_uses_pool_id_and_validates_token_order(self):
        repository = self.repository([{
            'pool_id': 7,
            'pool_application': 'chain-a:pool-app',
            'token_0': 'BBB',
            'token_1': 'AAA',
        }])

        resolved = repository.resolve_for_read(
            'AAA',
            'BBB',
            pool_id=7,
            pool_application='chain-a:pool-app',
        )

        self.assertEqual(resolved, (7, 'chain-a:pool-app', 'AAA', 'BBB', True))

    def test_resolve_for_read_prefers_pool_application_over_legacy_pool_id(self):
        repository = self.repository([{
            'pool_id': 7,
            'pool_application': 'chain-a:pool-app',
            'token_0': 'AAA',
            'token_1': 'BBB',
        }])

        resolved = repository.resolve_for_read(
            'AAA',
            'BBB',
            pool_id=1000,
            pool_application='chain-a:pool-app',
        )

        self.assertEqual(resolved, (7, 'chain-a:pool-app', 'AAA', 'BBB', False))

    def test_resolve_for_read_defaults_native_token(self):
        repository = self.repository([{
            'pool_id': 3,
            'pool_application': 'chain-a:native-pool',
            'token_0': 'TLINERA',
            'token_1': 'MEME',
        }])

        resolved = repository.resolve_for_read(None, 'MEME', pool_id=3)

        self.assertEqual(resolved, (3, 'chain-a:native-pool', 'TLINERA', 'MEME', False))

    def test_resolve_for_read_normalizes_zero_token_id_to_native(self):
        repository = self.repository([{
            'pool_id': 3,
            'pool_application': 'chain-a:native-pool',
            'token_0': 'MEME',
            'token_1': 'TLINERA',
        }])

        resolved = repository.resolve_for_read(
            'MEME',
            '0000000000000000000000000000000000000000000000000000000000000000',
            pool_id=3,
        )

        self.assertEqual(resolved, (3, 'chain-a:native-pool', 'MEME', 'TLINERA', False))

    def test_resolve_for_tokens_normalizes_zero_token_id_to_native(self):
        repository = self.repository([
            {
                'pool_id': 3,
                'pool_application': 'chain-a:native-pool',
                'token_0': 'TLINERA',
                'token_1': 'MEME',
            },
        ])

        resolved = repository.resolve_for_read(
            'MEME',
            '0000000000000000000000000000000000000000000000000000000000000000',
        )

        self.assertEqual(resolved, (3, 'chain-a:native-pool', 'MEME', 'TLINERA', True))

    def test_resolve_for_tokens_rejects_unknown_pair(self):
        repository = self.repository([])

        with self.assertRaisesRegex(Exception, 'Invalid token pair'):
            repository.resolve_for_tokens('AAA', 'BBB')

    def test_resolve_for_tokens_uses_projection_catalog_without_querying_pools_table(self):
        catalog = self.FakeProjectionPoolCatalogRepository([{
            'pool_id': 7,
            'pool_application': 'chain-a:pool-app',
            'token_0': 'AAA',
            'token_1': 'BBB',
        }])
        db = self.FakeDb()
        repository = PoolIdentityProjectionRepository(
            db,
            projection_pool_catalog_repository=catalog,
        )

        self.assertEqual(
            repository.resolve_for_tokens('AAA', 'BBB'),
            (7, 'chain-a:pool-app', 'AAA', 'BBB', False),
        )
        self.assertEqual(db.calls, [])
        self.assertEqual(catalog.calls, ['list_current_pools'])
