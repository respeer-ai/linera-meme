import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from registry.application_discovery_service import ApplicationDiscoveryService  # noqa: E402
from registry.application_registry import ApplicationRegistry  # noqa: E402


class ApplicationDiscoveryServiceTest(unittest.IsolatedAsyncioTestCase):
    class FakeRepository:
        def __init__(self):
            self.entries = {}

        def upsert_application(self, entry: dict) -> None:
            self.entries[entry['application_id']] = dict(entry)

        def get_application(self, application_id: str) -> dict | None:
            entry = self.entries.get(application_id)
            return None if entry is None else dict(entry)

        def list_applications(self, *, app_type: str | None = None, limit: int = 200) -> list[dict]:
            entries = [dict(entry) for entry in self.entries.values()]
            if app_type is not None:
                entries = [entry for entry in entries if entry['app_type'] == app_type]
            return entries[:limit]

    class FakeSwapCatalogClient:
        def __init__(self, pools):
            self.chain_id = 'chain-swap'
            self.application_id = 'app-swap'
            self._pools = pools

        async def list_pools(self) -> list[dict]:
            return list(self._pools)

    class FakeProxyCatalogClient:
        def __init__(self, meme_applications):
            self.chain_id = 'chain-proxy'
            self.application_id = 'app-proxy'
            self._meme_applications = meme_applications

        async def list_meme_applications(self) -> list[dict]:
            return list(self._meme_applications)

    async def test_discover_all_registers_pool_applications_from_swap_catalog(self):
        registry = ApplicationRegistry(self.FakeRepository())
        service = ApplicationDiscoveryService(
            application_registry=registry,
            swap_catalog_client=self.FakeSwapCatalogClient(
                [
                    {
                        'poolId': 7,
                        'token0': 'token-a',
                        'token1': 'token-b',
                        'poolApplication': {
                            'chain_id': 'chain-pool',
                            'owner': 'app-pool',
                        },
                    },
                ]
            ),
            swap_application_id='app-swap',
        )

        discovered = await service.discover_all()

        self.assertEqual(
            discovered,
            [
                {
                    'application_id': 'app-pool',
                    'app_type': 'pool',
                    'chain_id': 'chain-pool',
                    'creator_chain_id': 'chain-swap',
                    'owner': None,
                    'parent_application_id': 'app-swap',
                    'abi_version': None,
                    'discovered_from': 'swap_service',
                    'status': 'active',
                    'metadata_json': {
                        'pool_id': 7,
                        'token_0': 'token-a',
                        'token_1': 'token-b',
                    },
                }
            ],
        )

    async def test_discover_all_skips_pools_with_missing_application_identity(self):
        registry = ApplicationRegistry(self.FakeRepository())
        service = ApplicationDiscoveryService(
            application_registry=registry,
            swap_catalog_client=self.FakeSwapCatalogClient(
                [
                    {
                        'poolId': 7,
                        'token0': 'token-a',
                        'token1': 'token-b',
                        'poolApplication': {
                            'chain_id': 'chain-pool',
                        },
                    },
                ]
            ),
            swap_application_id='app-swap',
        )

        discovered = await service.discover_all()

        self.assertEqual(discovered, [])

    async def test_discover_all_normalizes_prefixed_pool_owner_ids(self):
        registry = ApplicationRegistry(self.FakeRepository())
        service = ApplicationDiscoveryService(
            application_registry=registry,
            swap_catalog_client=self.FakeSwapCatalogClient(
                [
                    {
                        'poolId': 8,
                        'token0': 'token-a',
                        'token1': None,
                        'poolApplication': {
                            'chain_id': 'chain-pool',
                            'owner': '0xabc123',
                        },
                    },
                ]
            ),
            swap_application_id='app-swap',
        )

        discovered = await service.discover_all()

        self.assertEqual(discovered[0]['application_id'], 'abc123')
        self.assertIsNotNone(registry.resolve('abc123'))
        self.assertIsNotNone(registry.resolve('0xabc123'))

    async def test_discover_all_registers_meme_applications_from_proxy_catalog(self):
        registry = ApplicationRegistry(self.FakeRepository())
        service = ApplicationDiscoveryService(
            application_registry=registry,
            proxy_catalog_client=self.FakeProxyCatalogClient(
                [
                    {
                        'chainId': 'chain-meme',
                        'token': 'app-meme',
                    },
                ]
            ),
            proxy_application_id='app-proxy',
        )

        discovered = await service.discover_all()

        self.assertEqual(
            discovered,
            [
                {
                    'application_id': 'app-meme',
                    'app_type': 'meme',
                    'chain_id': 'chain-meme',
                    'creator_chain_id': 'chain-proxy',
                    'owner': None,
                    'parent_application_id': 'app-proxy',
                    'abi_version': None,
                    'discovered_from': 'proxy_service',
                    'status': 'active',
                    'metadata_json': {},
                }
            ],
        )

    async def test_discover_all_skips_memes_with_missing_identity(self):
        registry = ApplicationRegistry(self.FakeRepository())
        service = ApplicationDiscoveryService(
            application_registry=registry,
            proxy_catalog_client=self.FakeProxyCatalogClient(
                [
                    {
                        'chainId': 'chain-meme',
                    },
                ]
            ),
            proxy_application_id='app-proxy',
        )

        discovered = await service.discover_all()

        self.assertEqual(discovered, [])
