from app.config import KlineAppConfig
from ingestion.chain_event_processor import ChainEventProcessor
from ingestion.catch_up_driver import CatchUpDriver
from ingestion.catch_up_runner import CatchUpRunner
from ingestion.chain_cursor_store import ChainCursorStore
from ingestion.block_parser import LayerOneBlockParser
from ingestion.coordinator import IngestionCoordinator
from integration.linera_graphql_chain_client import LineraGraphqlChainClient
from integration.linera_graphql_notification_listener import LineraGraphqlNotificationListener
from registry.application_registry import ApplicationRegistry
from registry.decoder_registry import DecoderRegistry
from storage.mysql.application_registry_repo import ApplicationRegistryRepository
from storage.mysql.connection import MysqlConnectionFactory
from storage.mysql.raw_repo import RawRepository


class AppBootstrap:
    def build_container(self, config: KlineAppConfig) -> dict[str, object]:
        connection = MysqlConnectionFactory().connect_from_app_config(config)
        raw_repository = RawRepository(connection)
        application_registry_repository = ApplicationRegistryRepository(connection)
        chain_cursor_store = ChainCursorStore(raw_repository)
        block_parser = LayerOneBlockParser()
        application_registry = ApplicationRegistry(application_registry_repository)
        decoder_registry = DecoderRegistry()
        container = {
            'config': config,
            'connection': connection,
            'raw_repository': raw_repository,
            'application_registry_repository': application_registry_repository,
            'application_registry': application_registry,
            'decoder_registry': decoder_registry,
            'chain_cursor_store': chain_cursor_store,
        }
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
            )
            container['catch_up_runner'] = catch_up_runner
            container['chain_event_processor'] = ChainEventProcessor(
                catch_up_runner=catch_up_runner,
                max_blocks_per_chain=config.catch_up_max_blocks_per_chain,
                allowed_chain_ids=config.catch_up_chain_ids,
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
