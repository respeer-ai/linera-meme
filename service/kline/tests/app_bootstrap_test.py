import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


mysql_stub = types.ModuleType('mysql')
mysql_connector_stub = types.ModuleType('mysql.connector')
mysql_connector_stub.connect = lambda **_kwargs: None
mysql_stub.connector = mysql_connector_stub
sys.modules['mysql'] = mysql_stub
sys.modules['mysql.connector'] = mysql_connector_stub

async_request_stub = types.ModuleType('async_request')


async def dummy_post(**_kwargs):
    raise AssertionError('async_request.post should not be called in bootstrap test')


async_request_stub.post = dummy_post
sys.modules['async_request'] = async_request_stub


from app.bootstrap import AppBootstrap  # noqa: E402
from app.config import KlineAppConfig  # noqa: E402
from app.lifecycle import AppLifecycle  # noqa: E402


class AppBootstrapTest(unittest.IsolatedAsyncioTestCase):
    class FakeConnection:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class FakeRawRepository:
        def __init__(self, connection):
            self.connection = connection
            self.ensure_schema_called = False

        def ensure_schema(self):
            self.ensure_schema_called = True

    class FakeApplicationRegistryRepository:
        def __init__(self, connection):
            self.connection = connection
            self.ensure_schema_called = False

        def ensure_schema(self):
            self.ensure_schema_called = True

        def upsert_application(self, _entry):
            return None

    class FakeFactory:
        def __init__(self, connection):
            self.connection = connection
            self.calls = []

        def connect_from_app_config(self, config):
            self.calls.append(config)
            return self.connection

    class FakeChainClient:
        def __init__(self, url, header_batch_limit=50):
            self.url = url
            self.header_batch_limit = header_batch_limit

    class FakeCatchUpDriver:
        def __init__(self):
            self.run_once_called = 0

        async def run_once(self):
            self.run_once_called += 1
            return {'total_ingested_count': 0}

    class FakeNotificationListener:
        def __init__(self):
            self.start_called = 0
            self.stop_called = 0

        async def start(self):
            self.start_called += 1

        async def stop(self):
            self.stop_called += 1

    class TestableBootstrap(AppBootstrap):
        def __init__(self, factory, repository_type, chain_client_type=None):
            self.factory = factory
            self.repository_type = repository_type
            self.chain_client_type = chain_client_type

        def build_container(self, config: KlineAppConfig) -> dict[str, object]:
            connection = self.factory.connect_from_app_config(config)
            raw_repository = self.repository_type(connection)
            application_registry_repository = AppBootstrapTest.FakeApplicationRegistryRepository(connection)
            container = {
                'config': config,
                'connection': connection,
                'raw_repository': raw_repository,
                'application_registry_repository': application_registry_repository,
                'application_registry': __import__('registry.application_registry', fromlist=['ApplicationRegistry']).ApplicationRegistry(application_registry_repository),
                'decoder_registry': __import__('registry.decoder_registry', fromlist=['DecoderRegistry']).DecoderRegistry(),
                'chain_cursor_store': object(),
            }
            if config.chain_graphql_url:
                chain_client = self.chain_client_type(
                    config.chain_graphql_url,
                    header_batch_limit=config.chain_graphql_header_batch_limit,
                )
                container['chain_client'] = chain_client
                container['block_parser'] = object()
                container['ingestion_coordinator'] = object()
                container['catch_up_runner'] = object()
                container['chain_event_processor'] = object()
                if config.catch_up_chain_ids:
                    container['catch_up_driver'] = AppBootstrapTest.FakeCatchUpDriver()
                    container['notification_listener'] = AppBootstrapTest.FakeNotificationListener()
            return container

    async def test_bootstrap_builds_container_and_lifecycle_manages_schema_and_close(self):
        connection = self.FakeConnection()
        bootstrap = self.TestableBootstrap(
            factory=self.FakeFactory(connection),
            repository_type=self.FakeRawRepository,
        )
        config = KlineAppConfig(
            database_host='db',
            database_port='3306',
            database_name='kline',
            database_username='user',
            database_password='pass',
        )

        container = bootstrap.build_container(config)
        lifecycle = AppLifecycle()
        await lifecycle.startup(container)
        await lifecycle.shutdown(container)

        self.assertIs(container['config'], config)
        self.assertIn('chain_cursor_store', container)
        self.assertTrue(container['raw_repository'].ensure_schema_called)
        self.assertTrue(container['application_registry_repository'].ensure_schema_called)
        self.assertTrue(connection.closed)

    async def test_bootstrap_wires_chain_client_when_graphql_url_present(self):
        connection = self.FakeConnection()
        bootstrap = self.TestableBootstrap(
            factory=self.FakeFactory(connection),
            repository_type=self.FakeRawRepository,
            chain_client_type=self.FakeChainClient,
        )
        config = KlineAppConfig(
            database_host='db',
            database_port='3306',
            database_name='kline',
            database_username='user',
            database_password='pass',
            chain_graphql_url='https://linera.example/graphql',
            chain_graphql_header_batch_limit=12,
        )

        container = bootstrap.build_container(config)

        self.assertEqual(container['chain_client'].url, 'https://linera.example/graphql')
        self.assertEqual(container['chain_client'].header_batch_limit, 12)
        self.assertIn('chain_cursor_store', container)
        self.assertIn('application_registry', container)
        self.assertIn('decoder_registry', container)
        self.assertIn('block_parser', container)
        self.assertIn('ingestion_coordinator', container)
        self.assertIn('catch_up_runner', container)
        self.assertIn('chain_event_processor', container)

    async def test_bootstrap_wires_catch_up_driver_when_chain_list_present(self):
        connection = self.FakeConnection()
        bootstrap = self.TestableBootstrap(
            factory=self.FakeFactory(connection),
            repository_type=self.FakeRawRepository,
            chain_client_type=self.FakeChainClient,
        )
        config = KlineAppConfig(
            database_host='db',
            database_port='3306',
            database_name='kline',
            database_username='user',
            database_password='pass',
            chain_graphql_url='https://linera.example/graphql',
            catch_up_chain_ids=('chain-a', 'chain-b'),
            catch_up_max_blocks_per_chain=15,
        )

        container = bootstrap.build_container(config)

        self.assertIn('catch_up_driver', container)
        self.assertIn('notification_listener', container)

    async def test_lifecycle_runs_startup_catch_up_when_driver_present(self):
        connection = self.FakeConnection()
        bootstrap = self.TestableBootstrap(
            factory=self.FakeFactory(connection),
            repository_type=self.FakeRawRepository,
            chain_client_type=self.FakeChainClient,
        )
        config = KlineAppConfig(
            database_host='db',
            database_port='3306',
            database_name='kline',
            database_username='user',
            database_password='pass',
            chain_graphql_url='https://linera.example/graphql',
            catch_up_chain_ids=('chain-a',),
            catch_up_on_startup=True,
        )

        container = bootstrap.build_container(config)
        lifecycle = AppLifecycle()

        await lifecycle.startup(container)

        self.assertEqual(container['catch_up_driver'].run_once_called, 1)

    async def test_lifecycle_skips_startup_catch_up_when_disabled(self):
        connection = self.FakeConnection()
        bootstrap = self.TestableBootstrap(
            factory=self.FakeFactory(connection),
            repository_type=self.FakeRawRepository,
            chain_client_type=self.FakeChainClient,
        )
        config = KlineAppConfig(
            database_host='db',
            database_port='3306',
            database_name='kline',
            database_username='user',
            database_password='pass',
            chain_graphql_url='https://linera.example/graphql',
            catch_up_chain_ids=('chain-a',),
            catch_up_on_startup=False,
        )

        container = bootstrap.build_container(config)
        lifecycle = AppLifecycle()

        await lifecycle.startup(container)

        self.assertEqual(container['catch_up_driver'].run_once_called, 0)

    async def test_lifecycle_starts_and_stops_notification_listener(self):
        connection = self.FakeConnection()
        bootstrap = self.TestableBootstrap(
            factory=self.FakeFactory(connection),
            repository_type=self.FakeRawRepository,
            chain_client_type=self.FakeChainClient,
        )
        config = KlineAppConfig(
            database_host='db',
            database_port='3306',
            database_name='kline',
            database_username='user',
            database_password='pass',
            chain_graphql_url='https://linera.example/graphql',
            catch_up_chain_ids=('chain-a',),
        )

        container = bootstrap.build_container(config)
        lifecycle = AppLifecycle()

        await lifecycle.startup(container)
        await lifecycle.shutdown(container)

        self.assertEqual(container['notification_listener'].start_called, 1)
        self.assertEqual(container['notification_listener'].stop_called, 1)
