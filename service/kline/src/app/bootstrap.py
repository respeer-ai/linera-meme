from app.config import KlineAppConfig
from ingestion.chain_event_processor import ChainEventProcessor
from ingestion.catch_up_driver import CatchUpDriver
from ingestion.catch_up_runner import CatchUpRunner
from ingestion.chain_cursor_store import ChainCursorStore
from ingestion.block_parser import LayerOneBlockParser
from ingestion.coordinator import IngestionCoordinator
from ingestion.post_ingest_pipeline import PostIngestPipeline
from integration.linera_graphql_chain_client import LineraGraphqlChainClient
from integration.linera_graphql_notification_listener import LineraGraphqlNotificationListener
from integration.proxy_catalog_client import ProxyCatalogClient
from integration.swap_catalog_client import SwapCatalogClient
from market.market_derivation_replay_driver import MarketDerivationReplayDriver
from market.market_derivation_worker import MarketDerivationWorker
from market.position_metrics_snapshot_builder import PositionMetricsSnapshotBuilder
from market.position_metrics_snapshot_materializer import PositionMetricsSnapshotMaterializer
from market.settled_market_deriver import SettledMarketDeriver
from market.settled_market_materializer import SettledMarketMaterializer
from normalizer.decode_result_normalizer import DecodeResultNormalizer
from normalizer.normalized_event_materializer import NormalizedEventMaterializer
from normalizer.normalization_replay_driver import NormalizationReplayDriver
from normalizer.normalization_worker import NormalizationWorker
from registry.ams_operation_decoder import AmsOperationDecoder
from registry.application_discovery_service import ApplicationDiscoveryService
from registry.application_registry import ApplicationRegistry
from registry.ams_message_decoder import AmsMessageDecoder
from registry.blob_gateway_operation_decoder import BlobGatewayOperationDecoder
from registry.blob_gateway_message_decoder import BlobGatewayMessageDecoder
from registry.decode_scheduler import DecodeScheduler
from registry.decoder_dispatcher import DecoderDispatcher
from registry.decoder_registry import DecoderRegistry
from registry.rust_decoder_runner import RustDecoderRunner
from registry.meme_message_decoder import MemeMessageDecoder
from registry.meme_operation_decoder import MemeOperationDecoder
from registry.pool_message_decoder import PoolMessageDecoder
from registry.pool_event_decoder import PoolEventDecoder
from registry.pool_operation_decoder import PoolOperationDecoder
from registry.proxy_message_decoder import ProxyMessageDecoder
from registry.proxy_operation_decoder import ProxyOperationDecoder
from registry.swap_message_decoder import SwapMessageDecoder
from registry.swap_operation_decoder import SwapOperationDecoder
from storage.mysql.application_registry_repo import ApplicationRegistryRepository
from storage.mysql.connection import MysqlConnectionFactory
from storage.mysql.normalized_repo import NormalizedEventRepository
from storage.mysql.pool_state_snapshot_repo import PoolStateSnapshotRepository
from storage.mysql.position_metrics_snapshot_materialization_inputs_repo import PositionMetricsSnapshotMaterializationInputsRepository
from storage.mysql.position_state_snapshot_repo import PositionStateSnapshotRepository
from storage.mysql.processing_cursor_repo import ProcessingCursorRepository
from storage.mysql.raw_repo import RawRepository
from storage.mysql.settled_liquidity_change_repo import SettledLiquidityChangeRepository
from storage.mysql.settled_trade_repo import SettledTradeRepository


async def _refresh_discovered_chain_ids(container: dict[str, object]) -> tuple[str, ...]:
    application_discovery_service = container.get('application_discovery_service')
    if application_discovery_service is not None and hasattr(application_discovery_service, 'discover_all'):
        await application_discovery_service.discover_all()

    application_registry = container.get('application_registry')
    if application_registry is None or not hasattr(application_registry, 'list_known_applications'):
        return ()

    discovered_chain_ids = []
    for app_type in ('pool', 'meme'):
        applications = application_registry.list_known_applications(app_type=app_type, limit=1000)
        for application in applications:
            chain_id = application.get('chain_id')
            if chain_id is not None and str(chain_id).strip():
                discovered_chain_ids.append(str(chain_id))

    if not discovered_chain_ids:
        return ()

    normalized_chain_ids = tuple(sorted(set(discovered_chain_ids)))
    for key in ('chain_event_processor', 'catch_up_driver'):
        component = container.get(key)
        if component is not None and hasattr(component, 'add_chain_ids'):
            component.add_chain_ids(normalized_chain_ids)

    notification_listener = container.get('notification_listener')
    if notification_listener is not None and hasattr(notification_listener, 'add_chain_ids'):
        await notification_listener.add_chain_ids(normalized_chain_ids)
    return normalized_chain_ids


class AppBootstrap:
    def build_container(self, config: KlineAppConfig) -> dict[str, object]:
        connection = MysqlConnectionFactory().connect_from_app_config(config)
        raw_repository = RawRepository(connection)
        application_registry_repository = ApplicationRegistryRepository(connection)
        normalized_event_repository = NormalizedEventRepository(connection)
        settled_trade_repository = SettledTradeRepository(connection)
        settled_liquidity_change_repository = SettledLiquidityChangeRepository(connection)
        position_state_snapshot_repository = PositionStateSnapshotRepository(connection)
        pool_state_snapshot_repository = PoolStateSnapshotRepository(connection)
        position_metrics_snapshot_materialization_inputs_repository = PositionMetricsSnapshotMaterializationInputsRepository(connection)
        position_metrics_snapshot_builder = PositionMetricsSnapshotBuilder(
            snapshot_materialization_inputs_repository=position_metrics_snapshot_materialization_inputs_repository,
        )
        position_metrics_snapshot_materializer = PositionMetricsSnapshotMaterializer(
            snapshot_builder=position_metrics_snapshot_builder,
            position_state_snapshot_repository=position_state_snapshot_repository,
            pool_state_snapshot_repository=pool_state_snapshot_repository,
        )
        processing_cursor_repository = ProcessingCursorRepository(connection)
        chain_cursor_store = ChainCursorStore(raw_repository)
        block_parser = LayerOneBlockParser()
        application_registry = ApplicationRegistry(application_registry_repository)
        decoder_registry = DecoderRegistry()
        decoder_registry.register_known_pairs(
            (
                ('pool', 'operation'),
                ('pool', 'message'),
                ('pool', 'event'),
                ('swap', 'operation'),
                ('swap', 'message'),
                ('meme', 'operation'),
                ('meme', 'message'),
                ('proxy', 'operation'),
                ('proxy', 'message'),
                ('ams', 'operation'),
                ('ams', 'message'),
                ('blob-gateway', 'operation'),
                ('blob-gateway', 'message'),
            )
        )
        decoder_registry.register(
            app_type='pool',
            payload_kind='operation',
            decoder=PoolOperationDecoder(),
        )
        decoder_registry.register(
            app_type='pool',
            payload_kind='message',
            decoder=PoolMessageDecoder(),
        )
        decoder_registry.register(
            app_type='pool',
            payload_kind='event',
            decoder=PoolEventDecoder(),
        )
        decoder_registry.register(
            app_type='swap',
            payload_kind='operation',
            decoder=SwapOperationDecoder(),
        )
        decoder_registry.register(
            app_type='swap',
            payload_kind='message',
            decoder=SwapMessageDecoder(),
        )
        decoder_registry.register(
            app_type='meme',
            payload_kind='operation',
            decoder=MemeOperationDecoder(),
        )
        decoder_registry.register(
            app_type='meme',
            payload_kind='message',
            decoder=MemeMessageDecoder(),
        )
        decoder_registry.register(
            app_type='blob-gateway',
            payload_kind='operation',
            decoder=BlobGatewayOperationDecoder(),
        )
        decoder_registry.register(
            app_type='blob-gateway',
            payload_kind='message',
            decoder=BlobGatewayMessageDecoder(),
        )
        decoder_registry.register(
            app_type='proxy',
            payload_kind='operation',
            decoder=ProxyOperationDecoder(),
        )
        decoder_registry.register(
            app_type='proxy',
            payload_kind='message',
            decoder=ProxyMessageDecoder(),
        )
        decoder_registry.register(
            app_type='ams',
            payload_kind='operation',
            decoder=AmsOperationDecoder(),
        )
        decoder_registry.register(
            app_type='ams',
            payload_kind='message',
            decoder=AmsMessageDecoder(),
        )
        decoder_dispatcher = DecoderDispatcher(
            application_registry=application_registry,
            decoder_registry=decoder_registry,
        )
        decode_scheduler = DecodeScheduler(
            decoder_dispatcher,
            runner=RustDecoderRunner(),
        )
        decode_result_normalizer = DecodeResultNormalizer()
        normalized_event_materializer = NormalizedEventMaterializer(
            decode_result_normalizer=decode_result_normalizer,
            normalized_event_repository=normalized_event_repository,
        )
        normalization_worker = NormalizationWorker(
            decode_scheduler=decode_scheduler,
            normalized_event_materializer=normalized_event_materializer,
            processing_cursor_repository=processing_cursor_repository,
        )
        normalization_replay_driver = NormalizationReplayDriver(
            raw_repository=raw_repository,
            processing_cursor_repository=processing_cursor_repository,
            normalization_worker=normalization_worker,
            batch_limit=config.normalization_replay_batch_limit,
        )
        settled_market_deriver = SettledMarketDeriver()
        settled_market_materializer = SettledMarketMaterializer(
            settled_market_deriver=settled_market_deriver,
            settled_trade_repository=settled_trade_repository,
            settled_liquidity_change_repository=settled_liquidity_change_repository,
            position_metrics_snapshot_materializer=position_metrics_snapshot_materializer,
        )
        market_derivation_worker = MarketDerivationWorker(
            settled_market_materializer=settled_market_materializer,
            processing_cursor_repository=processing_cursor_repository,
        )
        market_derivation_replay_driver = MarketDerivationReplayDriver(
            normalized_event_repository=normalized_event_repository,
            processing_cursor_repository=processing_cursor_repository,
            market_derivation_worker=market_derivation_worker,
            batch_limit=config.market_derivation_replay_batch_limit,
        )
        post_ingest_pipeline = PostIngestPipeline(
            normalization_replay_driver=normalization_replay_driver,
            market_derivation_replay_driver=market_derivation_replay_driver,
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
            'position_metrics_snapshot_materialization_inputs_repository': position_metrics_snapshot_materialization_inputs_repository,
            'position_metrics_snapshot_builder': position_metrics_snapshot_builder,
            'position_metrics_snapshot_materializer': position_metrics_snapshot_materializer,
            'processing_cursor_repository': processing_cursor_repository,
            'application_registry': application_registry,
            'decoder_registry': decoder_registry,
            'decoder_dispatcher': decoder_dispatcher,
            'decode_scheduler': decode_scheduler,
            'decode_result_normalizer': decode_result_normalizer,
            'normalized_event_materializer': normalized_event_materializer,
            'normalization_worker': normalization_worker,
            'normalization_replay_driver': normalization_replay_driver,
            'settled_market_deriver': settled_market_deriver,
            'settled_market_materializer': settled_market_materializer,
            'market_derivation_worker': market_derivation_worker,
            'market_derivation_replay_driver': market_derivation_replay_driver,
            'post_ingest_pipeline': post_ingest_pipeline,
            'chain_cursor_store': chain_cursor_store,
        }
        if config.swap_host and config.swap_chain_id and config.swap_application_id:
            swap_catalog_client = SwapCatalogClient(
                host=config.swap_host,
                chain_id=config.swap_chain_id,
                application_id=config.swap_application_id,
                query_base_url=f'http://{config.swap_host}/api/swap/query',
            )
            container['swap_catalog_client'] = swap_catalog_client
        if config.proxy_host and config.proxy_chain_id and config.proxy_application_id:
            proxy_catalog_client = ProxyCatalogClient(
                host=config.proxy_host,
                chain_id=config.proxy_chain_id,
                application_id=config.proxy_application_id,
                query_base_url=f'http://{config.proxy_host}/api/proxy/query',
            )
            container['proxy_catalog_client'] = proxy_catalog_client
        if 'swap_catalog_client' in container or 'proxy_catalog_client' in container:
            container['application_discovery_service'] = ApplicationDiscoveryService(
                application_registry=application_registry,
                swap_catalog_client=container.get('swap_catalog_client'),
                swap_application_id=config.swap_application_id,
                proxy_catalog_client=container.get('proxy_catalog_client'),
                proxy_application_id=config.proxy_application_id,
            )
        if config.chain_graphql_url:
            chain_client = LineraGraphqlChainClient(
                config.chain_graphql_url,
                header_batch_limit=config.chain_graphql_header_batch_limit,
            )
            ingestion_coordinator = IngestionCoordinator(
                chain_client=chain_client,
                block_parser=block_parser,
                raw_repository=raw_repository,
            )
            container['chain_client'] = chain_client
            container['block_parser'] = block_parser
            container['ingestion_coordinator'] = ingestion_coordinator
            catch_up_runner = CatchUpRunner(
                chain_cursor_store=chain_cursor_store,
                ingestion_coordinator=ingestion_coordinator,
                post_ingest_pipeline=post_ingest_pipeline,
            )
            container['catch_up_runner'] = catch_up_runner
            container['chain_event_processor'] = ChainEventProcessor(
                catch_up_runner=catch_up_runner,
                max_blocks_per_chain=config.catch_up_max_blocks_per_chain,
                allowed_chain_ids=config.catch_up_chain_ids,
                registry_refresh=lambda: _refresh_discovered_chain_ids(container),
            )
            if config.catch_up_chain_ids:
                container['catch_up_driver'] = CatchUpDriver(
                    catch_up_runner=catch_up_runner,
                    chain_ids=config.catch_up_chain_ids,
                    max_blocks_per_chain=config.catch_up_max_blocks_per_chain,
                )
                container['notification_listener'] = LineraGraphqlNotificationListener(
                    graphql_url=config.chain_graphql_url,
                    websocket_url=config.chain_graphql_ws_url,
                    chain_ids=config.catch_up_chain_ids,
                    chain_event_processor=container['chain_event_processor'],
                    reconnect_delay_seconds=config.notification_reconnect_delay_seconds,
                )
        return container
