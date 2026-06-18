import asyncio
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
    class FakeBackgroundService:
        def __init__(self):
            self.started = asyncio.Event()
            self.stopped = False

        async def run(self):
            self.started.set()
            while not self.stopped:
                await asyncio.sleep(0.001)

        def stop(self):
            self.stopped = True

    class FakeRealtimeDb:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    class FakeServices:
        def __init__(self):
            self._realtime_db = None
            self._market_data_event_publisher = None
            self._market_data_event_publisher_task = None
            self._candle_finality_scheduler = None
            self._candle_finality_scheduler_task = None

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

    async def test_startup_schedules_observability_without_blocking_realtime_services(self):
        realtime_db = self.FakeRealtimeDb()
        publisher = self.FakeBackgroundService()
        scheduler = self.FakeBackgroundService()
        events = []

        class Supervisor:
            def start_in_background(self):
                events.append('observability_scheduled')
                return None

            async def shutdown(self):
                events.append('observability_shutdown')

        def build_publisher(created_db):
            self.assertIs(created_db, realtime_db)
            events.append('publisher_built')
            return publisher

        def build_scheduler(created_db):
            self.assertIs(created_db, realtime_db)
            events.append('scheduler_built')
            return scheduler

        lifecycle = KlineServiceLifecycle(
            db_config={'host': 'db', 'port': '3306', 'db_name': 'kline', 'username': 'user', 'password': 'pass'},
            build_market_data_event_publisher=build_publisher,
            build_candle_finality_scheduler=build_scheduler,
            observability_supervisor=Supervisor(),
            services=self.FakeServices(),
        )

        original_db_type = sys.modules['kline_service_lifecycle'].Db
        sys.modules['kline_service_lifecycle'].Db = lambda *_args, **_kwargs: realtime_db
        try:
            await lifecycle.startup()
            await asyncio.wait_for(publisher.started.wait(), timeout=1)
            await asyncio.wait_for(scheduler.started.wait(), timeout=1)
            await lifecycle.shutdown()
        finally:
            sys.modules['kline_service_lifecycle'].Db = original_db_type

        self.assertEqual(events, [
            'observability_scheduled',
            'publisher_built',
            'scheduler_built',
            'observability_shutdown',
        ])
        self.assertTrue(publisher.stopped)
        self.assertTrue(scheduler.stopped)
        self.assertTrue(realtime_db.closed)

    async def test_startup_fails_open_when_observability_start_raises(self):
        realtime_db = self.FakeRealtimeDb()
        publisher = self.FakeBackgroundService()
        scheduler = self.FakeBackgroundService()

        class FailingSupervisor:
            def start_in_background(self):
                raise RuntimeError('startup failed')

            async def shutdown(self):
                return None

        lifecycle = KlineServiceLifecycle(
            db_config={'host': 'db', 'port': '3306', 'db_name': 'kline', 'username': 'user', 'password': 'pass'},
            build_market_data_event_publisher=lambda created_db: publisher if created_db is realtime_db else publisher,
            build_candle_finality_scheduler=lambda created_db: scheduler if created_db is realtime_db else scheduler,
            observability_supervisor=FailingSupervisor(),
            services=self.FakeServices(),
        )

        original_db_type = sys.modules['kline_service_lifecycle'].Db
        sys.modules['kline_service_lifecycle'].Db = lambda *_args, **_kwargs: realtime_db
        try:
            await lifecycle.startup()
            await asyncio.wait_for(publisher.started.wait(), timeout=1)
            await asyncio.wait_for(scheduler.started.wait(), timeout=1)
            await lifecycle.shutdown()
        finally:
            sys.modules['kline_service_lifecycle'].Db = original_db_type

        self.assertIsNone(lifecycle.realtime_db)
        self.assertIsNone(lifecycle.market_data_event_publisher_task)
        self.assertIsNone(lifecycle.candle_finality_scheduler_task)
        self.assertTrue(publisher.stopped)
        self.assertTrue(scheduler.stopped)
        self.assertTrue(realtime_db.closed)


if __name__ == '__main__':
    unittest.main()
