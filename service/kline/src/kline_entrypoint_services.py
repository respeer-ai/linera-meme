from kline_runtime import KlineRuntime
from kline_service_lifecycle import KlineServiceLifecycle


class KlineEntrypointServices:
    def __init__(
        self,
        *,
        db,
        observability_config,
        swap,
        websocket_manager,
        db_config,
        observability_supervisor,
        market_data_event_queue=None,
    ):
        self._db = db
        self._observability_config = observability_config
        self._swap = swap
        self._websocket_manager = websocket_manager
        self._db_config = db_config
        self._observability_supervisor = observability_supervisor
        self._realtime_db = None
        self._market_data_event_publisher = None
        self._market_data_event_publisher_task = None
        self._candle_finality_scheduler = None
        self._candle_finality_scheduler_task = None
        self._market_data_event_queue = market_data_event_queue

    @property
    def realtime_db(self):
        return self._realtime_db

    @property
    def market_data_event_publisher(self):
        return self._market_data_event_publisher

    @property
    def market_data_event_publisher_task(self):
        return self._market_data_event_publisher_task

    @property
    def candle_finality_scheduler(self):
        return self._candle_finality_scheduler

    @property
    def candle_finality_scheduler_task(self):
        return self._candle_finality_scheduler_task

    @property
    def market_data_event_queue(self):
        if self._market_data_event_queue is None:
            self._market_data_event_queue = self.runtime().build_market_data_event_queue()
        return self._market_data_event_queue

    def signature_tuple(self):
        return (
            self._realtime_db,
            self._market_data_event_publisher,
            self._market_data_event_publisher_task,
            self._candle_finality_scheduler,
            self._candle_finality_scheduler_task,
            self._market_data_event_queue,
        )

    def runtime(self) -> KlineRuntime:
        return KlineRuntime(
            db=self._db,
            realtime_db=self._realtime_db,
            observability_config=self._observability_config,
            swap=self._swap,
            websocket_manager=self._websocket_manager,
            market_data_event_queue=self._market_data_event_queue,
        )

    def lifecycle(self) -> KlineServiceLifecycle:
        return KlineServiceLifecycle(
            db_config=self._db_config,
            build_market_data_event_publisher=self.build_market_data_event_publisher_for_lifecycle,
            build_candle_finality_scheduler=self.build_candle_finality_scheduler_for_lifecycle,
            observability_supervisor=self._observability_supervisor,
            services=self,
        )

    def build_market_data_event_publisher_for_lifecycle(self, realtime_db):
        return self.runtime().build_market_data_event_publisher_for_db(realtime_db)

    def build_candle_finality_scheduler_for_lifecycle(self, realtime_db):
        return self.runtime().build_candle_finality_scheduler_for_db(realtime_db)
