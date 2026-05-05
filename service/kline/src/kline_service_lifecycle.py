import asyncio
import traceback

from db import Db


class KlineServiceLifecycle:
    def __init__(
        self,
        *,
        db_config: dict | None,
        build_ticker,
        observability_supervisor,
        services,
    ):
        self._db_config = db_config
        self._build_ticker = build_ticker
        self._observability_supervisor = observability_supervisor
        self._services = services

    @property
    def ticker(self):
        return self._services.ticker

    @property
    def ticker_db(self):
        return self._services.ticker_db

    @property
    def ticker_task(self):
        return self._services.ticker_task

    async def run_ticker_forever(self):
        while self.ticker is not None and self.ticker.running():
            try:
                await self.ticker.run()
            except Exception as exc:
                print(f'Ticker quiting ... {exc}')
                traceback.print_exc()
                await asyncio.sleep(10)

    async def startup(self):
        if self._db_config is None:
            return
        if self.ticker_task is not None:
            return

        ticker_db = Db(
            self._db_config['host'],
            self._db_config['port'],
            self._db_config['db_name'],
            self._db_config['username'],
            self._db_config['password'],
            False,
        )
        ticker = self._build_ticker(ticker_db)
        ticker_task = asyncio.create_task(self.run_ticker_forever())
        self._services._ticker = ticker
        self._services._ticker_db = ticker_db
        self._services._ticker_task = ticker_task
        if self._observability_supervisor is not None:
            try:
                self._observability_supervisor.start_in_background()
            except Exception as exc:
                print(f'Observability background startup failed open: {exc}')
                traceback.print_exc()

    async def shutdown(self):
        ticker = self.ticker
        ticker_task = self.ticker_task
        ticker_db = self.ticker_db
        if ticker is not None:
            ticker.stop()
        if ticker_task is not None:
            await ticker_task
        if ticker_db is not None:
            ticker_db.close()
        self._services._ticker = ticker
        self._services._ticker_db = None
        self._services._ticker_task = None
        if self._observability_supervisor is not None:
            await self._observability_supervisor.shutdown()
