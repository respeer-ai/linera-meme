import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


db_stub = types.ModuleType('db')
db_stub.Db = object
sys.modules.setdefault('db', db_stub)


from kline_service_lifecycle import KlineServiceLifecycle  # noqa: E402


class KlineServiceLifecycleTest(unittest.IsolatedAsyncioTestCase):
    class FakeTicker:
        def __init__(self):
            self.stopped = False
            self.run_calls = 0

        def running(self):
            return not self.stopped

        async def run(self):
            self.run_calls += 1
            self.stopped = True

        def stop(self):
            self.stopped = True

    class FakeTickerDb:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class FakeServices:
        def __init__(self):
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

    async def test_startup_fails_open_when_observability_background_start_raises_synchronously(self):
        ticker_db = self.FakeTickerDb()
        ticker = self.FakeTicker()

        class FailingSupervisor:
            def start_in_background(self):
                raise RuntimeError('background start failed')

            async def shutdown(self):
                return None

        lifecycle = KlineServiceLifecycle(
            db_config={'host': 'db', 'port': '3306', 'db_name': 'kline', 'username': 'user', 'password': 'pass'},
            build_ticker=lambda created_db: ticker if created_db is ticker_db else ticker,
            observability_supervisor=FailingSupervisor(),
            services=self.FakeServices(),
        )

        original_db_type = sys.modules['kline_service_lifecycle'].Db
        sys.modules['kline_service_lifecycle'].Db = lambda *_args, **_kwargs: ticker_db
        try:
            await lifecycle.startup()
            await lifecycle.shutdown()
        finally:
            sys.modules['kline_service_lifecycle'].Db = original_db_type

        self.assertIs(lifecycle.ticker, ticker)
        self.assertIsNone(lifecycle.ticker_db)
        self.assertIsNone(lifecycle.ticker_task)
        self.assertTrue(ticker.stopped)
        self.assertTrue(ticker_db.closed)
