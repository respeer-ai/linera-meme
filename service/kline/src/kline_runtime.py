from app.config import KlineAppConfig
from app.observability_facade import ObservabilityFacade
from app.observability_runtime import ObservabilityRuntime
from app.observability_supervisor import ObservabilitySupervisor
from position_metrics_bootstrap import PositionMetricsBootstrap
from query.handlers.kline import KlineHandler
from query.handlers.position_metrics_noop_diagnostic_recorder import PositionMetricsNoopDiagnosticRecorder
from query.handlers.positions import PositionsHandler
from query.handlers.transactions import TransactionsHandler
from query.read_models.candles import CandlesReadModel
from query.read_models.position_metrics_protocol_fee_split_semantics import PositionMetricsProtocolFeeSplitSemantics
from query.read_models.positions import PositionsReadModel
from query.read_models.virtual_positions import VirtualPositionsReadModel
from query.read_models.transactions import TransactionsReadModel
from query.serializers.kline import KlineSerializer
from query.serializers.positions import PositionsSerializer
from query.serializers.transactions import TransactionsSerializer
from storage.mysql.debug_traces_query_repo import DebugTracesQueryRepository
from storage.mysql.diagnostic_events_query_repo import DiagnosticEventsQueryRepository
from storage.mysql.market_stats_projection_repo import MarketStatsProjectionRepository
from storage.mysql.position_metrics_diagnostic_recorder import PositionMetricsDiagnosticRecorder
from storage.mysql.position_metrics_positions_projection_repo import PositionMetricsPositionsProjectionRepository
from storage.mysql.position_metrics_replay_facts_projection_repo import PositionMetricsReplayFactsProjectionRepository
from storage.mysql.position_metrics_snapshot_inputs_projection_repo import PositionMetricsSnapshotInputsProjectionRepository
from storage.mysql.pool_catalog_projection_repo import PoolCatalogProjectionRepository
from storage.mysql.pool_state_projection_repo import PoolStateProjectionRepository
from storage.mysql.projection_pool_catalog_repo import ProjectionPoolCatalogRepository
from storage.mysql.settled_liquidity_projection_repo import SettledLiquidityProjectionRepository
from storage.mysql.settled_pool_history_projection_repo import SettledPoolHistoryProjectionRepository
from storage.mysql.settled_trade_projection_repo import SettledTradeProjectionRepository
from storage.mysql.transaction_watermarks_query_repo import TransactionWatermarksQueryRepository
from subscription import WebSocketManager
from websocket_candle_reader import WebsocketCandleReader


class KlineRuntime:
    def __init__(
        self,
        *,
        db,
        ticker_db,
        observability_config: dict | None,
        swap,
        websocket_manager,
    ):
        self._db = db
        self._ticker_db = ticker_db
        self._observability_config = observability_config
        self._swap = swap
        self._websocket_manager = websocket_manager
        self._position_metrics_protocol_fee_split_semantics = PositionMetricsProtocolFeeSplitSemantics()
        self._position_metrics_public_api = PositionMetricsBootstrap().public_api()

    def position_metrics_protocol_fee_split_semantics(self) -> PositionMetricsProtocolFeeSplitSemantics:
        return self._position_metrics_protocol_fee_split_semantics

    def position_metrics_public_api(self):
        return self._position_metrics_public_api

    def settled_trade_projection_repository(self):
        self.require_db()
        return SettledTradeProjectionRepository(self._db)

    def settled_liquidity_projection_repository(self):
        self.require_db()
        return SettledLiquidityProjectionRepository(self._db)

    def settled_pool_history_projection_repository(self):
        self.require_db()
        return SettledPoolHistoryProjectionRepository(
            settled_trade_projection_repo=self.settled_trade_projection_repository(),
            settled_liquidity_projection_repo=self.settled_liquidity_projection_repository(),
        )

    def position_metrics_positions_projection_repository(self):
        self.require_db()
        return PositionMetricsPositionsProjectionRepository(
            self._db,
            settled_liquidity_projection_repo=self.settled_liquidity_projection_repository(),
        )

    def position_metrics_snapshot_inputs_projection_repository(self):
        self.require_db()
        return PositionMetricsSnapshotInputsProjectionRepository(self._db)

    def position_metrics_replay_facts_projection_repository(self):
        self.require_db()
        return PositionMetricsReplayFactsProjectionRepository(
            settled_liquidity_projection_repo=self.settled_liquidity_projection_repository(),
            settled_pool_history_projection_repo=self.settled_pool_history_projection_repository(),
        )

    def market_stats_projection_repository(self):
        self.require_db()
        return MarketStatsProjectionRepository(self._db)

    def projection_pool_catalog_repository(self):
        self.require_db()
        return ProjectionPoolCatalogRepository(
            pool_catalog_projection_repository=PoolCatalogProjectionRepository(
                getattr(self._db, 'connection', self._db)
            ),
            pool_state_projection_repository=PoolStateProjectionRepository(self._db),
        )

    def get_ticker_stats(self, *, interval: str) -> list[dict]:
        return self.market_stats_projection_repository().get_ticker(interval=interval)

    def get_pool_stats(self, *, interval: str) -> list[dict]:
        return self.market_stats_projection_repository().get_pool_stats(interval=interval)

    def diagnostic_events_query_repository(self):
        self.require_db()
        return DiagnosticEventsQueryRepository(self._db)

    def debug_traces_query_repository(self):
        self.require_db()
        return DebugTracesQueryRepository(self._db)

    def kline_handler(self) -> KlineHandler:
        return KlineHandler(
            CandlesReadModel(self.settled_trade_projection_repository()),
            KlineSerializer(),
        )

    def websocket_candle_reader(self) -> WebsocketCandleReader:
        return WebsocketCandleReader(CandlesReadModel(self.settled_trade_projection_repository()))

    def ticker_transaction_history_repository(self):
        return self.settled_pool_history_projection_repository()

    def ticker_transaction_watermarks_repository(self):
        self.require_db()
        return TransactionWatermarksQueryRepository(self._db)

    def transactions_handler(self) -> TransactionsHandler:
        return TransactionsHandler(
            TransactionsReadModel(self.settled_trade_projection_repository()),
            TransactionsSerializer(),
        )

    def positions_handler(self) -> PositionsHandler:
        return PositionsHandler(
            PositionsReadModel(
                self.settled_liquidity_projection_repository(),
                virtual_positions_read_model=self.virtual_positions_read_model(),
            ),
            PositionsSerializer(),
        )

    def virtual_positions_read_model(self) -> VirtualPositionsReadModel | None:
        return VirtualPositionsReadModel(
            projection_repository=self.settled_liquidity_projection_repository(),
            snapshot_inputs_projection_repository=self.position_metrics_snapshot_inputs_projection_repository(),
        )

    def position_metrics_diagnostic_recorder(self) -> PositionMetricsDiagnosticRecorder:
        if self._db is None:
            return PositionMetricsNoopDiagnosticRecorder()
        return PositionMetricsDiagnosticRecorder(self._db)

    def build_observability_supervisor(self):
        if self._observability_config is None:
            return ObservabilitySupervisor(None)
        required_keys = {
            'database_host',
            'database_port',
            'database_name',
            'database_username',
            'database_password',
            'chain_graphql_url',
        }
        if not required_keys.issubset(set(self._observability_config.keys())):
            return ObservabilitySupervisor(None)
        runtime = ObservabilityRuntime(KlineAppConfig(**self._observability_config))
        return ObservabilitySupervisor(runtime)

    def build_observability_facade(self):
        return ObservabilityFacade(self.build_observability_supervisor())

    def build_ticker(self):
        if self._websocket_manager is None:
            raise RuntimeError('WebSocket manager is not initialized')
        if self._swap is None:
            raise RuntimeError('Swap client is not initialized')
        return self.build_ticker_for_db(self._ticker_db)

    def build_websocket_manager(self):
        return WebSocketManager(
            self._swap,
            self.websocket_candle_reader(),
            self.projection_pool_catalog_repository(),
        )

    def build_ticker_for_db(self, ticker_db):
        if ticker_db is None:
            raise RuntimeError('Ticker Db client is not initialized')
        if self._websocket_manager is None:
            raise RuntimeError('WebSocket manager is not initialized')
        from ticker import Ticker
        return Ticker(
            self._websocket_manager,
            self._swap,
            self.projection_pool_catalog_repository(),
            candle_reader=self.websocket_candle_reader(),
            transaction_history_repository=self.ticker_transaction_history_repository(),
            transaction_watermarks_repository=self.ticker_transaction_watermarks_repository(),
        )

    async def get_protocol_stats(self) -> dict:
        pools = self.projection_pool_catalog_repository().list_current_pools()
        return self.market_stats_projection_repository().get_protocol_stats(pools=pools)

    def require_db(self):
        if self._db is None:
            raise RuntimeError('Db client is not initialized')
