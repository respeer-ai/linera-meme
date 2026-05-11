import asyncio
import traceback

from db import Db


class KlineServiceLifecycle:
    def __init__(
        self,
        *,
        db_config: dict | None,
        build_market_data_event_publisher,
        build_candle_finality_scheduler,
        observability_supervisor,
        services,
    ):
        self._db_config = db_config
        self._build_market_data_event_publisher = build_market_data_event_publisher
        self._build_candle_finality_scheduler = build_candle_finality_scheduler
        self._observability_supervisor = observability_supervisor
        self._services = services

    @property
    def realtime_db(self):
        return self._services.realtime_db

    @property
    def market_data_event_publisher(self):
        return self._services.market_data_event_publisher

    @property
    def market_data_event_publisher_task(self):
        return self._services.market_data_event_publisher_task

    @property
    def candle_finality_scheduler(self):
        return self._services.candle_finality_scheduler

    @property
    def candle_finality_scheduler_task(self):
        return self._services.candle_finality_scheduler_task

    async def startup(self):
        if self._db_config is None:
            return
        if self.market_data_event_publisher_task is not None:
            return

        if self._observability_supervisor is not None:
            try:
                await self._observability_supervisor.start_if_configured()
            except Exception as exc:
                print(f'Observability startup failed open: {exc}')
                traceback.print_exc()

        realtime_db = Db(
            self._db_config['host'],
            self._db_config['port'],
            self._db_config['db_name'],
            self._db_config['username'],
            self._db_config['password'],
            False,
        )
        publisher = self._build_market_data_event_publisher(realtime_db)
        finality_scheduler = self._build_candle_finality_scheduler(realtime_db)
        self._services._realtime_db = realtime_db
        self._services._market_data_event_publisher = publisher
        self._services._candle_finality_scheduler = finality_scheduler
        self._services._market_data_event_publisher_task = asyncio.create_task(publisher.run())
        self._services._candle_finality_scheduler_task = asyncio.create_task(finality_scheduler.run())

    async def shutdown(self):
        publisher = self.market_data_event_publisher
        publisher_task = self.market_data_event_publisher_task
        finality_scheduler = self.candle_finality_scheduler
        finality_task = self.candle_finality_scheduler_task
        realtime_db = self.realtime_db
        if publisher is not None:
            publisher.stop()
        if finality_scheduler is not None:
            finality_scheduler.stop()
        for task in (publisher_task, finality_task):
            if task is not None:
                task.cancel()
        if publisher_task is not None or finality_task is not None:
            await asyncio.gather(
                *[task for task in (publisher_task, finality_task) if task is not None],
                return_exceptions=True,
            )
        if realtime_db is not None:
            realtime_db.close()
        self._services._market_data_event_publisher = None
        self._services._market_data_event_publisher_task = None
        self._services._candle_finality_scheduler = None
        self._services._candle_finality_scheduler_task = None
        self._services._realtime_db = None
        if self._observability_supervisor is not None:
            await self._observability_supervisor.shutdown()
