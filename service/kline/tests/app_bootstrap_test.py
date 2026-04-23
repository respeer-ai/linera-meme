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

    class FakeFactory:
        def __init__(self, connection):
            self.connection = connection
            self.calls = []

        def connect_from_app_config(self, config):
            self.calls.append(config)
            return self.connection

    class TestableBootstrap(AppBootstrap):
        def __init__(self, factory, repository_type):
            self.factory = factory
            self.repository_type = repository_type

        def build_container(self, config: KlineAppConfig) -> dict[str, object]:
            connection = self.factory.connect_from_app_config(config)
            raw_repository = self.repository_type(connection)
            return {
                'config': config,
                'connection': connection,
                'raw_repository': raw_repository,
            }

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
        self.assertTrue(container['raw_repository'].ensure_schema_called)
        self.assertTrue(connection.closed)
