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
    ):
        self._db = db
        self._observability_config = observability_config
        self._swap = swap
        self._websocket_manager = websocket_manager
        self._db_config = db_config
        self._observability_supervisor = observability_supervisor
        self._ticker = None
        self._ticker_db = None
        self._ticker_task = None

    @property
    def ticker(self):
        return self._ticker

    @property
    def ticker_db(self):
        return self._ticker_db

    @property
    def ticker_task(self):
        return self._ticker_task

    def signature_tuple(self):
        return (
            self._ticker_db,
            self._ticker,
            self._ticker_task,
        )

    def runtime(self) -> KlineRuntime:
        return KlineRuntime(
            db=self._db,
            ticker_db=self._ticker_db,
            observability_config=self._observability_config,
            swap=self._swap,
            websocket_manager=self._websocket_manager,
        )

    def lifecycle(self) -> KlineServiceLifecycle:
        return KlineServiceLifecycle(
            db_config=self._db_config,
            build_ticker=self.build_ticker_for_lifecycle,
            observability_supervisor=self._observability_supervisor,
            services=self,
        )

    def build_ticker_for_lifecycle(self, ticker_db):
        return self.runtime().build_ticker_for_db(ticker_db)
