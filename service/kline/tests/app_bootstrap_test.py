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
from app.observability_facade import ObservabilityFacade  # noqa: E402
from app.observability_runtime import ObservabilityRuntime  # noqa: E402
from app.observability_supervisor import ObservabilitySupervisor  # noqa: E402


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

    class FakeNormalizedEventRepository:
        def __init__(self, connection):
            self.connection = connection
            self.ensure_schema_called = False

        def ensure_schema(self):
            self.ensure_schema_called = True

    class FakeSettledTradeRepository:
        def __init__(self, connection):
            self.connection = connection
            self.ensure_schema_called = False

        def ensure_schema(self):
            self.ensure_schema_called = True

    class FakeSettledLiquidityChangeRepository:
        def __init__(self, connection):
            self.connection = connection
            self.ensure_schema_called = False

        def ensure_schema(self):
            self.ensure_schema_called = True

    class FakePositionStateSnapshotRepository:
        def __init__(self, connection):
            self.connection = connection
            self.ensure_schema_called = False

        def ensure_schema(self):
            self.ensure_schema_called = True

    class FakePoolStateSnapshotRepository:
        def __init__(self, connection):
            self.connection = connection
            self.ensure_schema_called = False

        def ensure_schema(self):
            self.ensure_schema_called = True

    class FakeProcessingCursorRepository:
        def __init__(self, connection):
            self.connection = connection

        def list_cursors(self, limit=200):
            return [{'cursor_name': 'layer2_normalizer', 'limit': limit}]

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
            normalized_event_repository = AppBootstrapTest.FakeNormalizedEventRepository(connection)
            settled_trade_repository = AppBootstrapTest.FakeSettledTradeRepository(connection)
            settled_liquidity_change_repository = AppBootstrapTest.FakeSettledLiquidityChangeRepository(connection)
            position_state_snapshot_repository = AppBootstrapTest.FakePositionStateSnapshotRepository(connection)
            pool_state_snapshot_repository = AppBootstrapTest.FakePoolStateSnapshotRepository(connection)
            processing_cursor_repository = AppBootstrapTest.FakeProcessingCursorRepository(connection)
            application_registry = __import__('registry.application_registry', fromlist=['ApplicationRegistry']).ApplicationRegistry(application_registry_repository)
            decoder_registry = __import__('registry.decoder_registry', fromlist=['DecoderRegistry']).DecoderRegistry()
            decoder_registry.register_known_pairs((('pool', 'operation'),))
            decoder_registry.register(
                app_type='pool',
                payload_kind='operation',
                decoder=object(),
            )
            decoder_registry.register_known_pairs((('pool', 'message'),))
            decoder_registry.register(
                app_type='pool',
                payload_kind='message',
                decoder=object(),
            )
            decoder_registry.register_known_pairs((('swap', 'operation'),))
            decoder_registry.register(
                app_type='swap',
                payload_kind='operation',
                decoder=object(),
            )
            decoder_registry.register_known_pairs((('swap', 'message'),))
            decoder_registry.register(
                app_type='swap',
                payload_kind='message',
                decoder=object(),
            )
            decoder_registry.register_known_pairs((('meme', 'operation'),))
            decoder_registry.register(
                app_type='meme',
                payload_kind='operation',
                decoder=object(),
            )
            decoder_registry.register_known_pairs((('meme', 'message'),))
            decoder_registry.register(
                app_type='meme',
                payload_kind='message',
                decoder=object(),
            )
            decoder_registry.register_known_pairs((('blob-gateway', 'operation'),))
            decoder_registry.register(
                app_type='blob-gateway',
                payload_kind='operation',
                decoder=object(),
            )
            decoder_registry.register_known_pairs((('proxy', 'operation'),))
            decoder_registry.register(
                app_type='proxy',
                payload_kind='operation',
                decoder=object(),
            )
            decoder_registry.register_known_pairs((('ams', 'operation'),))
            decoder_registry.register(
                app_type='ams',
                payload_kind='operation',
                decoder=object(),
            )
            container = {
                'config': config,
                'connection': connection,
                'raw_repository': raw_repository,
                'application_registry_repository': application_registry_repository,
                'normalized_event_repository': normalized_event_repository,
                'settled_trade_repository': settled_trade_repository,
                'settled_liquidity_change_repository': settled_liquidity_change_repository,
                'position_state_snapshot_repository': position_state_snapshot_repository,
                'pool_state_snapshot_repository': pool_state_snapshot_repository,
                'processing_cursor_repository': processing_cursor_repository,
                'application_registry': application_registry,
                'decoder_registry': decoder_registry,
                'decoder_dispatcher': __import__('registry.decoder_dispatcher', fromlist=['DecoderDispatcher']).DecoderDispatcher(
                    application_registry=application_registry,
                    decoder_registry=decoder_registry,
                ),
                'decode_scheduler': object(),
                'decode_result_normalizer': object(),
                'normalized_event_materializer': object(),
                'normalization_worker': object(),
                'normalization_replay_driver': object(),
                'settled_market_deriver': object(),
                'settled_market_materializer': object(),
                'market_derivation_worker': object(),
                'market_derivation_replay_driver': object(),
                'chain_cursor_store': object(),
            }
            if config.swap_host and config.swap_chain_id and config.swap_application_id:
                container['swap_catalog_client'] = object()
            if config.proxy_host and config.proxy_chain_id and config.proxy_application_id:
                container['proxy_catalog_client'] = object()
            if 'swap_catalog_client' in container or 'proxy_catalog_client' in container:
                container['application_discovery_service'] = object()
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
        self.assertTrue(container['normalized_event_repository'].ensure_schema_called)
        self.assertTrue(container['settled_trade_repository'].ensure_schema_called)
        self.assertTrue(container['settled_liquidity_change_repository'].ensure_schema_called)
        self.assertTrue(container['position_state_snapshot_repository'].ensure_schema_called)
        self.assertTrue(container['pool_state_snapshot_repository'].ensure_schema_called)
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
            swap_host='swap.example',
            swap_chain_id='chain-swap',
            swap_application_id='app-swap',
            proxy_host='proxy.example',
            proxy_chain_id='chain-proxy',
            proxy_application_id='app-proxy',
        )

        container = bootstrap.build_container(config)

        self.assertEqual(container['chain_client'].url, 'https://linera.example/graphql')
        self.assertEqual(container['chain_client'].header_batch_limit, 12)
        self.assertIn('chain_cursor_store', container)
        self.assertIn('application_registry', container)
        self.assertIn('decoder_registry', container)
        self.assertIn('decoder_dispatcher', container)
        self.assertIn('decode_scheduler', container)
        self.assertIn('decode_result_normalizer', container)
        self.assertIn('normalized_event_repository', container)
        self.assertIn('normalized_event_materializer', container)
        self.assertIn('processing_cursor_repository', container)
        self.assertIn('normalization_worker', container)
        self.assertIn('normalization_replay_driver', container)
        self.assertIn('settled_trade_repository', container)
        self.assertIn('settled_liquidity_change_repository', container)
        self.assertIn('position_state_snapshot_repository', container)
        self.assertIn('pool_state_snapshot_repository', container)
        self.assertIn('settled_market_deriver', container)
        self.assertIn('settled_market_materializer', container)
        self.assertIn('market_derivation_worker', container)
        self.assertIn('market_derivation_replay_driver', container)
        self.assertIn('application_discovery_service', container)
        self.assertIn('proxy_catalog_client', container)
        self.assertIn(
            {
                'app_type': 'pool',
                'payload_kind': 'operation',
                'implemented': True,
            },
            container['decoder_registry'].list_supported_pairs(),
        )
        self.assertIn(
            {
                'app_type': 'pool',
                'payload_kind': 'message',
                'implemented': True,
            },
            container['decoder_registry'].list_supported_pairs(),
        )
        self.assertIn(
            {
                'app_type': 'blob-gateway',
                'payload_kind': 'operation',
                'implemented': True,
            },
            container['decoder_registry'].list_supported_pairs(),
        )
        self.assertIn(
            {
                'app_type': 'proxy',
                'payload_kind': 'operation',
                'implemented': True,
            },
            container['decoder_registry'].list_supported_pairs(),
        )
        self.assertIn(
            {
                'app_type': 'ams',
                'payload_kind': 'operation',
                'implemented': True,
            },
            container['decoder_registry'].list_supported_pairs(),
        )
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

    async def test_observability_runtime_returns_stage_results_and_keeps_container_when_listener_fails(self):
        class StageFailingLifecycle(AppLifecycle):
            async def start_listener(self, container: dict[str, object]) -> None:
                await super().start_listener(container)
                raise RuntimeError('listener failed')

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
        runtime = ObservabilityRuntime(
            config,
            bootstrap=bootstrap,
            lifecycle=StageFailingLifecycle(),
        )

        stage_results = await runtime.start()

        self.assertIsNotNone(runtime.container)
        self.assertEqual(stage_results['schema']['status'], 'ready')
        self.assertEqual(stage_results['registry']['status'], 'ready')
        self.assertEqual(stage_results['startup_catch_up']['status'], 'ready')
        self.assertEqual(stage_results['listener']['status'], 'degraded')
        self.assertEqual(stage_results['listener']['error'], 'listener failed')

    async def test_observability_runtime_marks_registry_stage_degraded_when_discovery_fails(self):
        class DiscoveryFailingLifecycle(AppLifecycle):
            async def discover_registry(self, container: dict[str, object]) -> None:
                raise RuntimeError('discovery failed')

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
            swap_host='swap.example',
            swap_chain_id='chain-swap',
            swap_application_id='app-swap',
        )
        runtime = ObservabilityRuntime(
            config,
            bootstrap=bootstrap,
            lifecycle=DiscoveryFailingLifecycle(),
        )

        stage_results = await runtime.start()

        self.assertIsNotNone(runtime.container)
        self.assertEqual(stage_results['registry']['status'], 'degraded')
        self.assertEqual(stage_results['registry']['error'], 'discovery failed')

    async def test_observability_supervisor_exposes_stage_level_degradation(self):
        class StageFailingRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True
                return {
                    'schema': {'status': 'ready', 'error': None},
                    'registry': {'status': 'ready', 'error': None},
                    'startup_catch_up': {'status': 'degraded', 'error': 'catch-up failed'},
                    'listener': {'status': 'ready', 'error': None},
                    'decode_scheduler': {'status': 'ready', 'error': None},
                    'normalizer': {'status': 'ready', 'error': None},
                    'market_deriver': {'status': 'ready', 'error': None},
                }

            async def shutdown(self):
                self.started = False

        supervisor = ObservabilitySupervisor(StageFailingRuntime())

        started = await supervisor.start_if_configured()

        self.assertFalse(started)
        snapshot = supervisor.snapshot()
        self.assertEqual(snapshot['state'], 'degraded')
        self.assertEqual(
            snapshot['components']['startup_catch_up']['status'],
            'degraded',
        )
        self.assertEqual(
            snapshot['components']['startup_catch_up']['last_error'],
            'catch-up failed',
        )

    async def test_observability_supervisor_fails_open_when_runtime_startup_raises(self):
        class FailingRuntime:
            def is_started(self):
                return False

            async def start(self):
                raise RuntimeError('startup failed')

            async def shutdown(self):
                return None

        supervisor = ObservabilitySupervisor(FailingRuntime())

        started = await supervisor.start_if_configured()

        self.assertFalse(started)
        self.assertEqual(supervisor.snapshot()['state'], 'degraded')
        self.assertEqual(supervisor.snapshot()['last_error'], 'startup failed')

    async def test_observability_supervisor_marks_degraded_when_catch_up_fails(self):
        class FailingCatchUpRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True

            async def shutdown(self):
                self.started = False

            async def run_catch_up(self, *, chain_id, max_blocks):
                raise RuntimeError(f'catch-up failed for {chain_id}:{max_blocks}')

        supervisor = ObservabilitySupervisor(FailingCatchUpRuntime())
        await supervisor.start_if_configured()

        with self.assertRaisesRegex(RuntimeError, 'catch-up failed'):
            await supervisor.run_catch_up(chain_id='chain-a', max_blocks=5)

        self.assertEqual(supervisor.snapshot()['state'], 'degraded')

    async def test_observability_supervisor_marks_normalizer_degraded_when_replay_fails(self):
        class FailingNormalizationRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True

            async def shutdown(self):
                self.started = False

            async def run_normalization_replay(self, **_kwargs):
                raise RuntimeError('normalization replay failed')

        supervisor = ObservabilitySupervisor(FailingNormalizationRuntime())
        await supervisor.start_if_configured()

        with self.assertRaisesRegex(RuntimeError, 'normalization replay failed'):
            await supervisor.run_normalization_replay(
                raw_table='raw_operations',
                batch_limit=10,
                max_batches=2,
                reprocess_reason='manual',
            )

        snapshot = supervisor.snapshot()
        self.assertEqual(snapshot['state'], 'degraded')
        self.assertEqual(
            snapshot['components']['normalizer']['status'],
            'degraded',
        )

    async def test_observability_facade_returns_empty_payload_when_runtime_not_ready(self):
        supervisor = ObservabilitySupervisor(None)
        facade = ObservabilityFacade(supervisor)

        payload = facade.get_debug_observability(
            chain_ids=('chain-a',),
            run_statuses=('success',),
            anomaly_statuses=('open',),
            limit=10,
        )

        self.assertEqual(payload['status']['state'], 'disabled')
        self.assertEqual(
            payload['status']['components']['decode_scheduler']['status'],
            'idle',
        )
        self.assertEqual(
            payload['status']['components']['normalizer']['status'],
            'idle',
        )
        self.assertEqual(
            payload['status']['components']['market_deriver']['status'],
            'idle',
        )
        self.assertEqual(
            payload['status']['component_groups']['workers'],
            ['decode_scheduler', 'normalizer', 'market_deriver'],
        )
        self.assertEqual(payload['operator_actions'][0]['action'], 'configure_observability')
        self.assertEqual(payload['cursors'], [])
        self.assertEqual(payload['processing_cursors'], [])
        self.assertEqual(payload['recent_runs'], [])
        self.assertEqual(payload['anomalies'], [])

    async def test_observability_facade_marks_degraded_when_debug_export_fails(self):
        class FailingRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True

            async def shutdown(self):
                self.started = False

            def export_debug_observability(self, **_kwargs):
                raise RuntimeError('debug export failed')

        supervisor = ObservabilitySupervisor(FailingRuntime())
        await supervisor.start_if_configured()
        facade = ObservabilityFacade(supervisor)

        payload = facade.get_debug_observability(
            chain_ids=('chain-a',),
            run_statuses=('success',),
            anomaly_statuses=('open',),
            limit=10,
        )

        self.assertEqual(payload['status']['state'], 'degraded')
        self.assertEqual(payload['status']['last_error'], 'debug export failed')
        self.assertEqual(
            payload['status']['components']['debug_export']['status'],
            'degraded',
        )
        self.assertEqual(payload['operator_actions'][0]['action'], 'call_debug_observability_recover')
        self.assertEqual(payload['cursors'], [])

    async def test_observability_facade_can_recover_explicitly(self):
        class RecoverableRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True

            async def shutdown(self):
                self.started = False

        runtime = RecoverableRuntime()
        supervisor = ObservabilitySupervisor(runtime)
        supervisor.status.mark_degraded('prior failure')
        facade = ObservabilityFacade(supervisor)

        result = await facade.recover()

        self.assertTrue(result['recovered'])
        self.assertEqual(result['status']['state'], 'ready')

    async def test_observability_facade_can_run_normalization_replay(self):
        class ReplayRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True

            async def shutdown(self):
                self.started = False

            async def run_normalization_replay(self, **kwargs):
                return {'result': kwargs}

        supervisor = ObservabilitySupervisor(ReplayRuntime())
        await supervisor.start_if_configured()
        facade = ObservabilityFacade(supervisor)

        result = await facade.run_normalization_replay(
            raw_table='raw_operations',
            batch_limit=10,
            max_batches=3,
            reprocess_reason='manual',
        )

        self.assertEqual(result['result']['raw_table'], 'raw_operations')
        self.assertEqual(result['result']['max_batches'], 3)

    async def test_observability_facade_can_run_market_derivation_replay(self):
        class ReplayRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True

            async def shutdown(self):
                self.started = False

            async def run_market_derivation_replay(self, **kwargs):
                return {'result': kwargs}

        supervisor = ObservabilitySupervisor(ReplayRuntime())
        await supervisor.start_if_configured()
        facade = ObservabilityFacade(supervisor)

        result = await facade.run_market_derivation_replay(
            raw_table='raw_posted_messages',
            batch_limit=20,
            max_batches=4,
            reprocess_reason='manual',
        )

        self.assertEqual(result['result']['raw_table'], 'raw_posted_messages')
        self.assertEqual(result['result']['max_batches'], 4)

    async def test_observability_facade_surfaces_component_specific_operator_actions(self):
        class StageFailingRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True
                return {
                    'schema': {'status': 'degraded', 'error': 'schema failed'},
                    'registry': {'status': 'ready', 'error': None},
                    'startup_catch_up': {'status': 'degraded', 'error': 'catch-up failed'},
                    'listener': {'status': 'degraded', 'error': 'listener failed'},
                    'decode_scheduler': {'status': 'ready', 'error': None},
                    'normalizer': {'status': 'ready', 'error': None},
                    'market_deriver': {'status': 'ready', 'error': None},
                }

            async def shutdown(self):
                self.started = False

        supervisor = ObservabilitySupervisor(StageFailingRuntime())
        await supervisor.start_if_configured()
        facade = ObservabilityFacade(supervisor)

        payload = facade.get_debug_observability(
            chain_ids=(),
            run_statuses=(),
            anomaly_statuses=(),
            limit=10,
        )

        actions = {action['action'] for action in payload['operator_actions']}
        self.assertIn('call_debug_observability_recover', actions)
        self.assertIn('check_mysql_schema_and_permissions', actions)
        self.assertIn('run_targeted_catch_up_or_inspect_chain_client', actions)
        self.assertIn('check_graphql_ws_connectivity', actions)
        self.assertNotIn('none_decode_scheduler_not_started', actions)

    async def test_observability_facade_surfaces_normalizer_operator_action(self):
        class NormalizerFailingRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True
                return {
                    'schema': {'status': 'ready', 'error': None},
                    'registry': {'status': 'ready', 'error': None},
                    'startup_catch_up': {'status': 'ready', 'error': None},
                    'listener': {'status': 'ready', 'error': None},
                    'decode_scheduler': {'status': 'ready', 'error': None},
                    'normalizer': {'status': 'degraded', 'error': 'normalizer failed'},
                    'market_deriver': {'status': 'ready', 'error': None},
                }

            async def shutdown(self):
                self.started = False

        supervisor = ObservabilitySupervisor(NormalizerFailingRuntime())
        await supervisor.start_if_configured()
        facade = ObservabilityFacade(supervisor)

        payload = facade.get_debug_observability(
            chain_ids=(),
            run_statuses=(),
            anomaly_statuses=(),
            limit=10,
        )

        actions = {action['action'] for action in payload['operator_actions']}
        self.assertIn('run_normalization_replay_or_inspect_layer2_cursor', actions)

    async def test_observability_facade_surfaces_market_deriver_operator_action(self):
        class MarketDeriverFailingRuntime:
            def __init__(self):
                self.started = False

            def is_started(self):
                return self.started

            async def start(self):
                self.started = True
                return {
                    'schema': {'status': 'ready', 'error': None},
                    'registry': {'status': 'ready', 'error': None},
                    'startup_catch_up': {'status': 'ready', 'error': None},
                    'listener': {'status': 'ready', 'error': None},
                    'decode_scheduler': {'status': 'ready', 'error': None},
                    'normalizer': {'status': 'ready', 'error': None},
                    'market_deriver': {'status': 'degraded', 'error': 'market derivation failed'},
                }

            async def shutdown(self):
                self.started = False

        supervisor = ObservabilitySupervisor(MarketDeriverFailingRuntime())
        await supervisor.start_if_configured()
        facade = ObservabilityFacade(supervisor)

        payload = facade.get_debug_observability(
            chain_ids=(),
            run_statuses=(),
            anomaly_statuses=(),
            limit=10,
        )

        actions = {action['action'] for action in payload['operator_actions']}
        self.assertIn('run_market_derivation_replay_or_inspect_layer3_cursor', actions)

    async def test_observability_runtime_exports_processing_cursors(self):
        class DebugExportRuntime:
            def __init__(self):
                self.started = True
                self.container = {
                    'raw_repository': AppBootstrapTest.FakeRawRepository(AppBootstrapTest.FakeConnection()),
                    'processing_cursor_repository': AppBootstrapTest.FakeProcessingCursorRepository(
                        AppBootstrapTest.FakeConnection()
                    ),
                }

            def is_started(self):
                return self.started

            def export_debug_observability(self, **_kwargs):
                return {
                    'cursors': [],
                    'processing_cursors': [{'cursor_name': 'layer2_normalizer'}],
                    'recent_runs': [],
                    'anomalies': [],
                }

        supervisor = ObservabilitySupervisor(DebugExportRuntime())
        await supervisor.start_if_configured()
        facade = ObservabilityFacade(supervisor)

        payload = facade.get_debug_observability(
            chain_ids=(),
            run_statuses=(),
            anomaly_statuses=(),
            limit=10,
        )

        self.assertEqual(payload['processing_cursors'], [{'cursor_name': 'layer2_normalizer'}])
