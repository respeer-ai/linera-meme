import asyncio
import sys
import types
import unittest
from unittest.mock import AsyncMock, Mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


swap_stub = types.ModuleType('swap')
swap_stub.Pool = object
swap_stub.Transaction = object
sys.modules.setdefault('swap', swap_stub)

mysql_stub = types.ModuleType('mysql')
mysql_connector_stub = types.ModuleType('mysql.connector')
mysql_connector_stub.connect = None
mysql_stub.connector = mysql_connector_stub
sys.modules.setdefault('mysql', mysql_stub)
sys.modules.setdefault('mysql.connector', mysql_connector_stub)

pandas_stub = types.ModuleType('pandas')
numpy_stub = types.ModuleType('numpy')
sys.modules.setdefault('pandas', pandas_stub)
sys.modules.setdefault('numpy', numpy_stub)

from ticker import Ticker  # noqa: E402


class FakeDb:
    def __init__(self):
        self.points = {}
        self.persisted_pools = []
        self.persisted_transactions = []
        self.watermarks = {}
        self.transaction_bounds = {}
        self.transaction_ids = {}
        self.diagnostics = []

    def get_kline(self, token_0, token_1, start_at, end_at, interval, pool_id=None, pool_application=None):
        points = [
            point
            for (_pool_id, _token_reversed, point_interval, _bucket_start_ms), point in self.points.items()
            if point_interval == interval
            and point['token_0'] == token_0
            and point['token_1'] == token_1
            and start_at <= point['bucket_start_ms'] <= end_at
        ]
        points.sort(key=lambda point: point['bucket_start_ms'])
        return (token_0, token_1, start_at, end_at, points)

    def new_pools(self, pools):
        self.persisted_pools.append(pools)

    def new_transactions(self, pool, transactions):
        self.persisted_transactions.append((pool.pool_id, transactions))
        return transactions

    def get_latest_transaction_watermarks(self):
        return dict(self.watermarks)

    def get_pool_transaction_id_bounds(self, pool_id, pool_application=None):
        return self.transaction_bounds.get((pool_id, pool_application))

    def get_pool_transaction_ids(self, pool_id, pool_application=None, start_id=None, end_id=None):
        ids = list(self.transaction_ids.get((pool_id, pool_application), []))
        lower_bound = 0 if start_id is None else int(start_id)
        upper_bound = 2 ** 32 - 1 if end_id is None else int(end_id)
        return [
            transaction_id
            for transaction_id in ids
            if lower_bound <= int(transaction_id) <= upper_bound
        ]

    def record_diagnostic_event(self, **kwargs):
        self.diagnostics.append(dict(kwargs))


def make_pool(pool_id=7, token_0='AAA', token_1='BBB'):
    return types.SimpleNamespace(
        pool_id=pool_id,
        token_0=token_0,
        token_1=token_1,
        pool_application=types.SimpleNamespace(chain_id='chain', owner='app'),
    )


def make_pool_identity(pool_id=7):
    return (pool_id, 'chain', 'app')


class TickerIncrementalPayloadTest(unittest.TestCase):
    def test_builds_incremental_payload_with_only_changed_candles(self):
        db = FakeDb()
        db.points[(7, False, '5min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_299_999,
            'is_final': False,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'base_volume': 14.0,
            'quote_volume': 35.0,
        }
        db.points[(7, True, '5min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'token_0': 'BBB',
            'token_1': 'AAA',
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_299_999,
            'is_final': False,
            'open': 0.5,
            'high': 0.5,
            'low': 0.33,
            'close': 0.33,
            'base_volume': 32.0,
            'quote_volume': 16.0,
        }
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_120_000)
        pool = make_pool()

        payload = ticker.build_incremental_kline_payload(
            pool,
            [
                {
                    'transaction_id': 10,
                    'transaction_type': 'BuyToken0',
                    'token_reversed': False,
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 10,
                    'transaction_type': 'BuyToken0',
                    'token_reversed': True,
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 11,
                    'transaction_type': 'BuyToken0',
                    'token_reversed': False,
                    'created_at': 1_800_000_030_000,
                },
            ],
        )

        self.assertEqual(payload['5min'], [
            {
                'pool_id': 7,
                'pool_application': 'chain:app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'interval': '5min',
                'start_at': 1_800_000_000_000,
                'end_at': 1_800_000_299_999,
                'points': [db.points[(7, False, '5min', 1_800_000_000_000)]],
            },
            {
                'pool_id': 7,
                'pool_application': 'chain:app',
                'token_0': 'BBB',
                'token_1': 'AAA',
                'interval': '5min',
                'start_at': 1_800_000_000_000,
                'end_at': 1_800_000_299_999,
                'points': [db.points[(7, True, '5min', 1_800_000_000_000)]],
            },
        ])

    def test_ignores_non_trade_transactions_and_missing_candle_points(self):
        ticker = Ticker(manager=None, swap=None, db=FakeDb())
        pool = make_pool()

        payload = ticker.build_incremental_kline_payload(
            pool,
            [
                {
                    'transaction_id': 10,
                    'transaction_type': 'AddLiquidity',
                    'token_reversed': False,
                    'created_at': 1_800_000_001_000,
                },
            ],
        )

        self.assertEqual(payload, {})

    def test_http_and_websocket_use_identical_closed_bucket_payload(self):
        db = FakeDb()
        db.points[(7, False, '1min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_059_999,
            'is_final': True,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'base_volume': 14.0,
            'quote_volume': 35.0,
        }
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_120_000)
        pool = make_pool()

        websocket_payload = ticker.build_incremental_kline_payload(
            pool,
            [{
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }],
        )['1min'][0]['points'][0]
        self.assertEqual(websocket_payload, db.points[(7, False, '1min', 1_800_000_000_000)])

    def test_builds_incremental_payload_with_gap_backfill_points_between_emitted_and_new_bucket(self):
        db = FakeDb()
        db.points[(7, False, '10min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_599_999,
            'is_final': True,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'base_volume': 10.0,
            'quote_volume': 25.0,
        }
        db.points[(7, False, '10min', 1_800_000_600_000)] = {
            'timestamp': 1_800_000_600_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_600_000,
            'bucket_end_ms': 1_800_001_199_999,
            'is_final': True,
            'open': 3.0,
            'high': 3.0,
            'low': 3.0,
            'close': 3.0,
            'base_volume': 0.0,
            'quote_volume': 0.0,
        }
        db.points[(7, False, '10min', 1_800_001_200_000)] = {
            'timestamp': 1_800_001_200_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_001_200_000,
            'bucket_end_ms': 1_800_001_799_999,
            'is_final': False,
            'open': 3.0,
            'high': 4.0,
            'low': 3.0,
            'close': 4.0,
            'base_volume': 5.0,
            'quote_volume': 20.0,
        }
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_001_250_000)
        ticker.last_emitted_bucket_starts[('AAA', 'BBB', '10min')] = 1_800_000_000_000
        pool = make_pool()

        payload = ticker.build_incremental_kline_payload(
            pool,
            [{
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_001_210_000,
            }],
        )

        self.assertEqual(payload['10min'][0]['start_at'], 1_800_000_600_000)
        self.assertEqual(
            [point['bucket_start_ms'] for point in payload['10min'][0]['points']],
            [1_800_000_600_000, 1_800_001_200_000],
        )

    def test_builds_rollover_payload_only_for_finalized_zero_volume_bucket_after_time_advance(self):
        db = FakeDb()
        db.points[(7, False, '1min', 1_800_000_060_000)] = {
            'timestamp': 1_800_000_060_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_060_000,
            'bucket_end_ms': 1_800_000_119_999,
            'is_final': False,
            'open': 3.0,
            'high': 3.0,
            'low': 3.0,
            'close': 3.0,
            'base_volume': 0.0,
            'quote_volume': 0.0,
        }
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_130_000)
        ticker.last_emitted_bucket_starts[('AAA', 'BBB', '1min')] = 1_800_000_000_000
        pool = make_pool()

        payload = ticker.build_rollover_kline_payload(pool)

        self.assertEqual(payload['1min'][0]['start_at'], 1_800_000_060_000)
        self.assertEqual(payload['1min'][0]['points'][0]['base_volume'], 0.0)
        self.assertEqual(payload['1min'][0]['points'][0]['close'], 3.0)

    def test_does_not_build_rollover_payload_for_current_unfinalized_empty_bucket(self):
        db = FakeDb()
        db.points[(7, False, '1min', 1_800_000_060_000)] = {
            'timestamp': 1_800_000_060_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_060_000,
            'bucket_end_ms': 1_800_000_119_999,
            'is_final': False,
            'open': 3.0,
            'high': 3.0,
            'low': 3.0,
            'close': 3.0,
            'base_volume': 0.0,
            'quote_volume': 0.0,
        }
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_070_000)
        ticker.last_emitted_bucket_starts[('AAA', 'BBB', '1min')] = 1_800_000_000_000
        pool = make_pool()

        payload = ticker.build_rollover_kline_payload(pool)

        self.assertEqual(payload, {})


class TickerRunIterationTest(unittest.IsolatedAsyncioTestCase):
    async def test_audit_historical_pool_history_detects_old_internal_missing_ids(self):
        db = FakeDb()
        db.transaction_bounds = {
            (7, 'chain:app'): {'min_transaction_id': 1000, 'max_transaction_id': 1010},
        }
        db.transaction_ids[(7, 'chain:app')] = [1000, 1001, 1002, 1004, 1005, 1010]
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.log_event = Mock()
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=1010)

        missing_ids = await ticker.audit_historical_pool_history(pool)

        self.assertEqual(missing_ids[:3], [1003, 1006, 1007])
        ticker.log_event.assert_called_once()
        self.assertEqual(ticker.log_event.call_args.args[0], 'pool_transactions_historical_gap_detected')
        self.assertEqual(db.diagnostics[0]['event_type'], 'historical_pool_history_gap')

    async def test_audit_historical_pool_history_only_scans_once_after_clean_pass(self):
        db = FakeDb()
        db.transaction_bounds = {
            (7, 'chain:app'): {'min_transaction_id': 1000, 'max_transaction_id': 1003},
        }
        db.transaction_ids[(7, 'chain:app')] = [1000, 1001, 1002, 1003]
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_120_000)
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=1003)

        self.assertEqual(await ticker.audit_historical_pool_history(pool), [])
        db.transaction_ids[(7, 'chain:app')] = [1000]
        self.assertEqual(await ticker.audit_historical_pool_history(pool), [])

    async def test_audit_recent_pool_history_detects_internal_missing_ids(self):
        db = FakeDb()
        db.transaction_ids[(7, 'chain:app')] = [351, 352, 354, 355, 400]
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.recent_backfill_transaction_count = 50
        ticker.log_event = Mock()
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=400)

        missing_ids = await ticker.audit_recent_pool_history(pool)

        self.assertEqual(missing_ids[:3], [353, 356, 357])
        ticker.log_event.assert_called_once()
        self.assertEqual(ticker.log_event.call_args.args[0], 'pool_transactions_recent_gap_detected')
        self.assertEqual(db.diagnostics[0]['event_type'], 'recent_pool_history_gap')

    async def test_run_iteration_repairs_missing_current_app_history_once_from_initial_transaction_id(self):
        db = FakeDb()
        db.transaction_bounds = {
            (7, 'chain:app'): {'min_transaction_id': 1500, 'max_transaction_id': 1510},
        }
        db.transaction_ids[(7, 'chain:app')] = list(range(1500, 1511))
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(manager=manager, swap=swap, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.recent_backfill_transaction_count = 0
        ticker.initial_transaction_id = 1000
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=1600)
        ticker.get_pools = AsyncMock(return_value=[pool])
        ticker.get_pool_transactions = AsyncMock(side_effect=[
            [{
                'transaction_id': 1000,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }, {
                'transaction_id': 1600,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_002_000,
            }],
            [{
                'transaction_id': 1600,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_002_000,
            }],
        ])

        await ticker.run_iteration({})

        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, 1000))
        self.assertEqual(ticker.get_pool_transactions.await_args_list[1].args, (pool, 1600))
        self.assertTrue(any(row['event_type'] == 'historical_repair_fetch' for row in db.diagnostics))

    async def test_run_iteration_logs_old_internal_gap_and_continues_incremental_sync(self):
        db = FakeDb()
        db.transaction_bounds = {
            (7, 'chain:app'): {'min_transaction_id': 1000, 'max_transaction_id': 7000},
        }
        db.transaction_ids[(7, 'chain:app')] = list(range(6501, 7001))
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(manager=manager, swap=swap, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.recent_backfill_transaction_count = 500
        ticker.initial_transaction_id = 1000
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=7000)
        ticker.get_pools = AsyncMock(return_value=[pool])
        ticker.get_pool_transactions = AsyncMock(return_value=[{
            'transaction_id': 7000,
            'transaction_type': 'BuyToken0',
            'token_reversed': False,
            'created_at': 1_800_000_002_000,
        }])

        last_timestamps = {make_pool_identity(): (1_800_000_001_000, 7000, 0)}
        await ticker.run_iteration(last_timestamps)

        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, 6501))
        self.assertEqual(ticker.get_pool_transactions.await_args_list[1].args, (pool, 7000))
        event_types = [row['event_type'] for row in db.diagnostics]
        self.assertIn('historical_pool_history_gap', event_types)
        self.assertIn('recent_backfill_fetch', event_types)
        self.assertIn('incremental_fetch', event_types)

    async def test_repair_historical_pool_history_skips_internal_gap_when_prefix_exists(self):
        db = FakeDb()
        db.transaction_bounds = {
            (7, 'chain:app'): {'min_transaction_id': 1000, 'max_transaction_id': 7000},
        }
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.initial_transaction_id = 1000
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=7000)
        ticker.get_pool_transactions = AsyncMock(return_value=[])

        await ticker.repair_historical_pool_history(pool, {})

        ticker.get_pool_transactions.assert_not_awaited()

    async def test_run_iteration_without_db_watermark_requests_full_incremental_window(self):
        db = FakeDb()
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(manager=manager, swap=swap, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.recent_backfill_transaction_count = 0
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=321)
        ticker.get_pools = AsyncMock(return_value=[pool])
        ticker.get_pool_transactions = AsyncMock(return_value=[])

        await ticker.run_iteration({})

        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, None))

    async def test_run_iteration_offloads_persistence_and_notifies_manager(self):
        db = FakeDb()
        db.points[(7, False, '1min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_059_999,
            'is_final': True,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'base_volume': 14.0,
            'quote_volume': 35.0,
        }
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(manager=manager, swap=swap, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.recent_backfill_transaction_count = 0
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=10)
        ticker.get_pools = AsyncMock(return_value=[pool])
        ticker.get_pool_transactions = AsyncMock(return_value=[{
            'transaction_id': 10,
            'transaction_type': 'BuyToken0',
            'token_reversed': False,
            'created_at': 1_800_000_001_000,
        }])

        last_timestamps = {}
        await ticker.run_iteration(last_timestamps)

        self.assertEqual(len(db.persisted_pools), 1)
        self.assertEqual(len(db.persisted_transactions), 1)
        self.assertEqual(last_timestamps, {make_pool_identity(): (1_800_000_001_000, 10, 0)})
        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, None))
        self.assertEqual(manager.notify.await_count, 2)
        self.assertEqual(manager.notify.await_args_list[0].args[0], 'kline')
        self.assertEqual(manager.notify.await_args_list[1].args[0], 'transactions')

    async def test_run_iteration_keeps_same_timestamp_new_transactions_live(self):
        db = FakeDb()
        db.points[(7, False, '1min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_059_999,
            'is_final': True,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'base_volume': 14.0,
            'quote_volume': 35.0,
        }
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(manager=manager, swap=swap, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.recent_backfill_transaction_count = 0
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=10)
        ticker.get_pools = AsyncMock(return_value=[pool])
        ticker.get_pool_transactions = AsyncMock(side_effect=[
            [{
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }],
            [{
                'transaction_id': 11,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }],
        ])

        last_timestamps = {}
        await ticker.run_iteration(last_timestamps)
        await ticker.run_iteration(last_timestamps)

        self.assertEqual(last_timestamps, {make_pool_identity(): (1_800_000_001_000, 11, 0)})
        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, None))
        self.assertEqual(ticker.get_pool_transactions.await_args_list[1].args, (pool, 10))
        self.assertEqual(manager.notify.await_args_list[0].args[0], 'kline')
        self.assertEqual(manager.notify.await_args_list[2].args[0], 'kline')
        second_kline_payload = manager.notify.await_args_list[2].args[1]
        self.assertEqual(second_kline_payload['1min'][0]['points'][0]['timestamp'], 1_800_000_000_000)

    async def test_run_bootstraps_last_timestamps_from_db_watermarks(self):
        db = FakeDb()
        db.watermarks = {make_pool_identity(): (1_800_000_001_000, 321, 0)}
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(manager=manager, swap=swap, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.recent_backfill_transaction_count = 0
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=999)
        ticker.get_pools = AsyncMock(return_value=[pool])
        ticker.get_pool_transactions = AsyncMock(side_effect=[
            [],
            asyncio.CancelledError(),
        ])

        with self.assertRaises(asyncio.CancelledError):
            await ticker.run()

        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, 321))

    async def test_run_iteration_backfills_recent_transactions_once_before_live_poll(self):
        db = FakeDb()
        db.transaction_ids[(7, 'chain:app')] = list(range(351, 401))
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(manager=manager, swap=swap, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.recent_backfill_transaction_count = 50
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=400)
        ticker.get_pools = AsyncMock(return_value=[pool])
        ticker.get_pool_transactions = AsyncMock(side_effect=[
            [{
                'transaction_id': 400,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }],
            [],
        ])

        last_timestamps = {}
        await ticker.run_iteration(last_timestamps)

        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, 351))
        self.assertEqual(ticker.get_pool_transactions.await_args_list[1].args, (pool, 400))
        self.assertEqual(last_timestamps, {make_pool_identity(): (1_800_000_001_000, 400, 0)})
        self.assertIn(make_pool_identity(), ticker.backfilled_pools)

    async def test_run_iteration_does_not_repeat_recent_backfill_after_first_pass(self):
        db = FakeDb()
        db.transaction_ids[(7, 'chain:app')] = list(range(351, 401))
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(manager=manager, swap=swap, db=db, now_ms=lambda: 1_800_000_120_000)
        ticker.recent_backfill_transaction_count = 50
        pool = make_pool()
        pool.latest_transaction = types.SimpleNamespace(transaction_id=400)
        ticker.get_pools = AsyncMock(return_value=[pool])
        ticker.get_pool_transactions = AsyncMock(side_effect=[
            [{
                'transaction_id': 400,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }],
            [],
            [],
        ])

        last_timestamps = {}
        await ticker.run_iteration(last_timestamps)
        await ticker.run_iteration(last_timestamps)

        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, 351))
        self.assertEqual(ticker.get_pool_transactions.await_args_list[1].args, (pool, 400))
        self.assertEqual(ticker.get_pool_transactions.await_args_list[2].args, (pool, 400))

    def test_find_missing_transaction_ids_returns_dense_gap_list(self):
        ticker = Ticker(manager=None, swap=None, db=FakeDb())

        missing_ids = ticker.find_missing_transaction_ids([1000, 1001, 1004, 1006], 1000, 1006)

        self.assertEqual(missing_ids, [1002, 1003, 1005])


if __name__ == '__main__':
    unittest.main()
