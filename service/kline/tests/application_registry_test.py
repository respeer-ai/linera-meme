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
