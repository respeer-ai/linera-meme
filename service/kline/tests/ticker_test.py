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
from websocket_candle_reader import WebsocketCandleReader  # noqa: E402


POOL_OWNER = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
POOL_CHAIN = 'chain'
POOL_APPLICATION = f'{POOL_OWNER}@{POOL_CHAIN}'


class FakeDb:
    def __init__(self):
        self.points = {}
        self.watermarks = {}
        self.pool_histories = {}

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

    def get_latest_transaction_watermarks(self):
        return dict(self.watermarks)

    def get_pool_transaction_history(self, *, pool_application, pool_id):
        return list(self.pool_histories.get((pool_id, pool_application), []))


class FakeCandleReader:
    def __init__(self, db):
        self.db = db
        self.calls = []

    def get_points(self, **kwargs):
        self.calls.append(dict(kwargs))
        return {
            'pool_id': kwargs['pool_id'],
            'pool_application': kwargs['pool_application'],
            'token_0': kwargs['token_0'],
            'token_1': kwargs['token_1'],
            'interval': kwargs['interval'],
            'start_at': kwargs['start_at'],
            'end_at': kwargs['end_at'],
            'points': self.db.get_kline(**kwargs)[4],
        }


def make_pool(pool_id=7, token_0='AAA', token_1='BBB'):
    return types.SimpleNamespace(
        pool_id=pool_id,
        token_0=token_0,
        token_1=token_1,
        pool_application=types.SimpleNamespace(chain_id=POOL_CHAIN, owner=POOL_OWNER),
    )


def make_pool_identity(pool_id=7):
    return (pool_id, POOL_CHAIN, POOL_OWNER)


class TickerIncrementalPayloadTest(unittest.TestCase):
    def test_websocket_candle_reader_exposes_get_points_for_ticker(self):
        read_model = Mock()
        read_model.get_points.return_value = {
            'pool_id': 7,
            'pool_application': POOL_APPLICATION,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'interval': '5m',
            'start_at': 1,
            'end_at': 2,
            'points': [],
        }
        reader = WebsocketCandleReader(read_model)

        payload = reader.get_points(
            token_0='AAA',
            token_1='BBB',
            start_at=1,
            end_at=2,
            interval='5min',
            pool_id=7,
            pool_application=POOL_APPLICATION,
        )

        read_model.get_points.assert_called_once_with(
            token_0='AAA',
            token_1='BBB',
            start_at=1,
            end_at=2,
            interval='5min',
            pool_id=7,
            pool_application=POOL_APPLICATION,
        )
        self.assertEqual(payload['interval'], '5min')

    def test_builds_incremental_payload_with_only_changed_candles(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
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
        ticker = Ticker(
            manager=None,
            swap=None,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_120_000,
        )
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
                'pool_application': POOL_APPLICATION,
                'token_0': 'AAA',
                'token_1': 'BBB',
                'interval': '5min',
                'start_at': 1_800_000_000_000,
                'end_at': 1_800_000_299_999,
                'points': [db.points[(7, False, '5min', 1_800_000_000_000)]],
            },
            {
                'pool_id': 7,
                'pool_application': POOL_APPLICATION,
                'token_0': 'BBB',
                'token_1': 'AAA',
                'interval': '5min',
                'start_at': 1_800_000_000_000,
                'end_at': 1_800_000_299_999,
                'points': [db.points[(7, True, '5min', 1_800_000_000_000)]],
            },
        ])
        self.assertTrue(candle_reader.calls)

    def test_ignores_non_trade_transactions_and_missing_candle_points(self):
        db = FakeDb()
        ticker = Ticker(
            manager=None,
            swap=None,
            pool_catalog_repository=None,
            candle_reader=FakeCandleReader(FakeDb()),
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
        )
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
        candle_reader = FakeCandleReader(db)
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
        ticker = Ticker(
            manager=None,
            swap=None,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_120_000,
        )
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

    def test_builds_incremental_payload_for_live_bucket_using_bucket_end_range(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
        db.points[(7, False, '1min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_059_999,
            'is_final': False,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'base_volume': 14.0,
            'quote_volume': 35.0,
        }
        ticker = Ticker(
            manager=None,
            swap=None,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_030_000,
        )
        pool = make_pool()

        payload = ticker.build_incremental_kline_payload(
            pool,
            [{
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }],
        )

        self.assertEqual(
            payload['1min'][0]['points'][0],
            db.points[(7, False, '1min', 1_800_000_000_000)],
        )
        self.assertEqual(candle_reader.calls[0]['end_at'], 1_800_000_059_999)

    def test_repeated_live_trades_in_same_bucket_do_not_advance_range_into_next_bucket(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
        db.points[(7, False, '1min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_059_999,
            'is_final': False,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'base_volume': 14.0,
            'quote_volume': 35.0,
        }
        ticker = Ticker(
            manager=None,
            swap=None,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_030_000,
        )
        pool = make_pool()

        first_payload = ticker.build_incremental_kline_payload(
            pool,
            [{
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }],
        )
        second_payload = ticker.build_incremental_kline_payload(
            pool,
            [{
                'transaction_id': 11,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_030_000,
            }],
        )

        self.assertEqual(first_payload['1min'][0]['points'][0]['base_volume'], 14.0)
        self.assertEqual(second_payload['1min'][0]['points'][0]['base_volume'], 14.0)
        one_min_calls = [call for call in candle_reader.calls if call['interval'] == '1min']
        self.assertEqual(one_min_calls[1]['start_at'], 1_800_000_000_000)
        self.assertEqual(one_min_calls[1]['end_at'], 1_800_000_059_999)

    def test_builds_incremental_payload_with_gap_backfill_points_between_emitted_and_new_bucket(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
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
        ticker = Ticker(
            manager=None,
            swap=None,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_001_250_000,
        )
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

        self.assertEqual(payload['10min'][0]['start_at'], 1_800_000_000_000)
        self.assertEqual(
            [point['bucket_start_ms'] for point in payload['10min'][0]['points']],
            [1_800_000_000_000, 1_800_000_600_000, 1_800_001_200_000],
        )

    def test_builds_rollover_payload_only_for_finalized_zero_volume_bucket_after_time_advance(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
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
        ticker = Ticker(
            manager=None,
            swap=None,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_130_000,
        )
        ticker.last_emitted_bucket_starts[('AAA', 'BBB', '1min')] = 1_800_000_000_000
        pool = make_pool()

        payload = ticker.build_rollover_kline_payload(pool)

        self.assertEqual(payload['1min'][0]['start_at'], 1_800_000_060_000)
        self.assertEqual(payload['1min'][0]['points'][0]['base_volume'], 0.0)
        self.assertEqual(payload['1min'][0]['points'][0]['close'], 3.0)

    def test_does_not_build_rollover_payload_for_current_unfinalized_empty_bucket(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
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
        ticker = Ticker(
            manager=None,
            swap=None,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_070_000,
        )
        ticker.last_emitted_bucket_starts[('AAA', 'BBB', '1min')] = 1_800_000_000_000
        pool = make_pool()

        payload = ticker.build_rollover_kline_payload(pool)

        self.assertEqual(payload, {})


class TickerRunIterationTest(unittest.IsolatedAsyncioTestCase):
    async def test_run_iteration_without_db_watermark_reads_full_projection_history(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
        db.pool_histories[(7, POOL_APPLICATION)] = [
            {
                'transaction_id': 321,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            },
        ]
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(
            manager=manager,
            swap=swap,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_120_000,
        )
        pool = make_pool()
        ticker.get_pools = AsyncMock(return_value=[pool])

        last_timestamps = {}
        await ticker.run_iteration(last_timestamps)

        self.assertEqual(last_timestamps, {make_pool_identity(): (1_800_000_001_000, 321, 0)})
        self.assertEqual(manager.notify.await_count, 2)

    async def test_run_iteration_accepts_liquidity_history_without_token_reversed(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
        db.pool_histories[(7, POOL_APPLICATION)] = [
            {
                'transaction_id': 1000,
                'transaction_type': 'AddLiquidity',
                'created_at': 1_800_000_001_000,
            },
        ]
        manager = types.SimpleNamespace(notify=AsyncMock())
        ticker = Ticker(
            manager=manager,
            swap=types.SimpleNamespace(),
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_120_000,
        )
        pool = make_pool()
        ticker.get_pools = AsyncMock(return_value=[pool])

        last_timestamps = {}
        await ticker.run_iteration(last_timestamps)

        self.assertEqual(last_timestamps, {make_pool_identity(): (1_800_000_001_000, 1000, 0)})
        self.assertEqual(manager.notify.await_args_list[0].args[1], {})

    async def test_run_iteration_notifies_manager_from_projection_history(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
        db.pool_histories[(7, POOL_APPLICATION)] = [{
            'transaction_id': 10,
            'transaction_type': 'BuyToken0',
            'token_reversed': False,
            'created_at': 1_800_000_001_000,
        }]
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
        ticker = Ticker(
            manager=manager,
            swap=swap,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_120_000,
        )
        pool = make_pool()
        ticker.get_pools = AsyncMock(return_value=[pool])

        last_timestamps = {}
        await ticker.run_iteration(last_timestamps)

        self.assertEqual(last_timestamps, {make_pool_identity(): (1_800_000_001_000, 10, 0)})
        self.assertEqual(manager.notify.await_count, 2)
        self.assertEqual(manager.notify.await_args_list[0].args[0], 'kline')
        self.assertEqual(manager.notify.await_args_list[1].args[0], 'transactions')

    async def test_run_iteration_keeps_same_timestamp_new_projection_transactions_live(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
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
        ticker = Ticker(
            manager=manager,
            swap=swap,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_120_000,
        )
        pool = make_pool()
        ticker.get_pools = AsyncMock(return_value=[pool])
        db.pool_histories[(7, POOL_APPLICATION)] = [{
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }]

        last_timestamps = {}
        await ticker.run_iteration(last_timestamps)

        db.pool_histories[(7, POOL_APPLICATION)] = [{
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }, {
                'transaction_id': 11,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }]
        await ticker.run_iteration(last_timestamps)

        self.assertEqual(last_timestamps, {make_pool_identity(): (1_800_000_001_000, 11, 0)})
        self.assertEqual(manager.notify.await_args_list[0].args[0], 'kline')
        self.assertEqual(manager.notify.await_args_list[2].args[0], 'kline')
        second_kline_payload = manager.notify.await_args_list[2].args[1]
        self.assertEqual(second_kline_payload['1min'][0]['points'][0]['timestamp'], 1_800_000_000_000)

    async def test_run_bootstraps_last_timestamps_from_db_watermarks(self):
        db = FakeDb()
        candle_reader = FakeCandleReader(db)
        db.watermarks = {make_pool_identity(): (1_800_000_001_000, 321, 0)}
        db.pool_histories[(7, POOL_APPLICATION)] = []
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(
            manager=manager,
            swap=swap,
            pool_catalog_repository=None,
            candle_reader=candle_reader,
            transaction_history_repository=db,
            transaction_watermarks_repository=db,
            now_ms=lambda: 1_800_000_120_000,
        )
        pool = make_pool()
        ticker.get_pools = AsyncMock(return_value=[pool])
        original_run_iteration = ticker.run_iteration

        async def fake_run_iteration(last_timestamps):
            await original_run_iteration(last_timestamps)
            raise asyncio.CancelledError()

        ticker.run_iteration = fake_run_iteration

        with self.assertRaises(asyncio.CancelledError):
            await ticker.run()

        self.assertEqual(manager.notify.await_count, 2)


if __name__ == '__main__':
    unittest.main()
