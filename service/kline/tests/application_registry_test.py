import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from app.config import KlineAppConfig  # noqa: E402
from registry.application_registry import ApplicationRegistry  # noqa: E402


class ApplicationRegistryTest(unittest.TestCase):
    class FakeRepository:
        def __init__(self):
            self.entries = {}
            self.upserts = []

        def upsert_application(self, entry: dict) -> None:
            self.upserts.append(dict(entry))
            self.entries[entry['application_id']] = dict(entry)

        def get_application(self, application_id: str) -> dict | None:
            entry = self.entries.get(application_id)
            return None if entry is None else dict(entry)

        def list_applications(self, *, app_type: str | None = None, limit: int = 200) -> list[dict]:
            entries = [dict(entry) for entry in self.entries.values()]
            if app_type is not None:
                entries = [entry for entry in entries if entry['app_type'] == app_type]
            return entries[:limit]

    def test_seed_from_config_registers_known_swap_application(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        config = KlineAppConfig(
            database_host='db',
            database_port='3306',
            database_name='kline',
            database_username='user',
            database_password='pass',
            swap_host='swap.example',
            swap_chain_id='chain-swap',
            swap_application_id='app-swap',
        )

        seeded = registry.seed_from_config(config)

        self.assertEqual(len(seeded), 1)
        self.assertEqual(repository.upserts[0]['application_id'], 'app-swap')
        self.assertEqual(repository.upserts[0]['app_type'], 'swap')
        self.assertEqual(repository.upserts[0]['discovered_from'], 'static_config')

    def test_seed_from_config_registers_known_proxy_application(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        config = KlineAppConfig(
            database_host='db',
            database_port='3306',
            database_name='kline',
            database_username='user',
            database_password='pass',
            proxy_host='proxy.example',
            proxy_chain_id='chain-proxy',
            proxy_application_id='app-proxy',
        )

        seeded = registry.seed_from_config(config)

        self.assertEqual(len(seeded), 1)
        self.assertEqual(repository.upserts[0]['application_id'], 'app-proxy')
        self.assertEqual(repository.upserts[0]['app_type'], 'proxy')
        self.assertEqual(repository.upserts[0]['discovered_from'], 'static_config')

    def test_register_known_application_can_be_resolved(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)

        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
            chain_id='chain-pool',
            discovered_from='manual',
            metadata_json={'token_0': 'a'},
        )

        self.assertEqual(
            registry.resolve('app-pool'),
            {
                'application_id': 'app-pool',
                'app_type': 'pool',
                'chain_id': 'chain-pool',
                'creator_chain_id': None,
                'owner': None,
                'parent_application_id': None,
                'abi_version': None,
                'discovered_from': 'manual',
                'status': 'active',
                'metadata_json': {'token_0': 'a'},
            },
        )

    def test_list_known_applications_can_filter_by_app_type(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
        )
        registry.register_known_application(
            application_id='app-swap',
            app_type='swap',
        )

        self.assertEqual(
            registry.list_known_applications(app_type='pool'),
            [
                {
                    'application_id': 'app-pool',
                    'app_type': 'pool',
                    'chain_id': None,
                    'creator_chain_id': None,
                    'owner': None,
                    'parent_application_id': None,
                    'abi_version': None,
                    'discovered_from': 'manual',
                    'status': 'active',
                    'metadata_json': None,
                }
            ],
        )

    def test_discover_application_accepts_supported_source_and_status(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)

        entry = registry.discover_application(
            application_id='app-proxy',
            app_type='proxy',
            discovered_from=ApplicationRegistry.SOURCE_PROXY_SERVICE,
            status=ApplicationRegistry.STATUS_UNKNOWN,
            metadata_json={'host': 'proxy.example'},
        )

        self.assertEqual(entry['discovered_from'], 'proxy_service')
        self.assertEqual(entry['status'], 'unknown')

    def test_discover_application_rejects_unsupported_source(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)

        with self.assertRaisesRegex(ValueError, 'unsupported discovered_from'):
            registry.discover_application(
                application_id='app-proxy',
                app_type='proxy',
                discovered_from='bad_source',
            )

    def test_discover_application_rejects_unsupported_status(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)

        with self.assertRaisesRegex(ValueError, 'unsupported status'):
            registry.discover_application(
                application_id='app-proxy',
                app_type='proxy',
                discovered_from=ApplicationRegistry.SOURCE_MANUAL,
                status='bad_status',
            )
