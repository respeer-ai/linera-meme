import sys
import types
import unittest
from unittest.mock import AsyncMock
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
from db import build_candle_point_payload  # noqa: E402


class FakeDb:
    def __init__(self):
        self.points = {}
        self.persisted_pools = []
        self.persisted_transactions = []

    def get_candle_point(self, pool_id, token_reversed, interval, bucket_start_ms):
        return self.points.get((pool_id, token_reversed, interval, bucket_start_ms))

    def new_pools(self, pools):
        self.persisted_pools.append(pools)

    def new_transactions(self, pool_id, transactions):
        self.persisted_transactions.append((pool_id, transactions))
        return transactions


class TickerIncrementalPayloadTest(unittest.TestCase):
    def test_builds_incremental_payload_with_only_changed_candles(self):
        db = FakeDb()
        db.points[(7, False, '5min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'base_volume': 14.0,
            'quote_volume': 35.0,
        }
        db.points[(7, True, '5min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'open': 0.5,
            'high': 0.5,
            'low': 0.33,
            'close': 0.33,
            'base_volume': 32.0,
            'quote_volume': 16.0,
        }
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_120_000)
        pool = types.SimpleNamespace(pool_id=7, token_0='AAA', token_1='BBB')

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
                'token_0': 'AAA',
                'token_1': 'BBB',
                'interval': '5min',
                'start_at': 1_800_000_000_000,
                'end_at': 1_800_000_299_999,
                'points': [{
                    **db.points[(7, False, '5min', 1_800_000_000_000)],
                    'bucket_start_ms': 1_800_000_000_000,
                    'bucket_end_ms': 1_800_000_299_999,
                    'is_final': False,
                }],
            },
            {
                'token_0': 'BBB',
                'token_1': 'AAA',
                'interval': '5min',
                'start_at': 1_800_000_000_000,
                'end_at': 1_800_000_299_999,
                'points': [{
                    **db.points[(7, True, '5min', 1_800_000_000_000)],
                    'bucket_start_ms': 1_800_000_000_000,
                    'bucket_end_ms': 1_800_000_299_999,
                    'is_final': False,
                }],
            },
        ])

    def test_ignores_non_trade_transactions_and_missing_candle_points(self):
        ticker = Ticker(manager=None, swap=None, db=FakeDb())
        pool = types.SimpleNamespace(pool_id=7, token_0='AAA', token_1='BBB')

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
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'base_volume': 14.0,
            'quote_volume': 35.0,
        }
        ticker = Ticker(manager=None, swap=None, db=db, now_ms=lambda: 1_800_000_120_000)
        pool = types.SimpleNamespace(pool_id=7, token_0='AAA', token_1='BBB')

        websocket_payload = ticker.build_incremental_kline_payload(
            pool,
            [{
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            }],
        )['1min'][0]['points'][0]

        http_payload = build_candle_point_payload(
            interval='1min',
            bucket_start_ms=1_800_000_000_000,
            point=db.points[(7, False, '1min', 1_800_000_000_000)],
            now_ms=1_800_000_120_000,
        )

        self.assertEqual(websocket_payload, http_payload)


class TickerRunIterationTest(unittest.IsolatedAsyncioTestCase):
    async def test_run_iteration_uses_pool_latest_transaction_to_seed_incremental_fetch(self):
        db = FakeDb()
        manager = types.SimpleNamespace(notify=AsyncMock())
        swap = types.SimpleNamespace()
        ticker = Ticker(manager=manager, swap=swap, db=db, now_ms=lambda: 1_800_000_120_000)
        pool = types.SimpleNamespace(
            pool_id=7,
            token_0='AAA',
            token_1='BBB',
            latest_transaction=types.SimpleNamespace(transaction_id=321),
        )
        ticker.get_pools = AsyncMock(return_value=[pool])
        ticker.get_pool_transactions = AsyncMock(return_value=[])

        await ticker.run_iteration({})

        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, 320))

    async def test_run_iteration_offloads_persistence_and_notifies_manager(self):
        db = FakeDb()
        db.points[(7, False, '1min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
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
        pool = types.SimpleNamespace(
            pool_id=7,
            token_0='AAA',
            token_1='BBB',
            latest_transaction=types.SimpleNamespace(transaction_id=10),
        )
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
        self.assertEqual(last_timestamps, {7: (1_800_000_001_000, 10, 0)})
        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, 9))
        self.assertEqual(manager.notify.await_count, 2)
        self.assertEqual(manager.notify.await_args_list[0].args[0], 'kline')
        self.assertEqual(manager.notify.await_args_list[1].args[0], 'transactions')

    async def test_run_iteration_keeps_same_timestamp_new_transactions_live(self):
        db = FakeDb()
        db.points[(7, False, '1min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
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
        pool = types.SimpleNamespace(
            pool_id=7,
            token_0='AAA',
            token_1='BBB',
            latest_transaction=types.SimpleNamespace(transaction_id=10),
        )
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

        self.assertEqual(last_timestamps, {7: (1_800_000_001_000, 11, 0)})
        self.assertEqual(ticker.get_pool_transactions.await_args_list[0].args, (pool, 9))
        self.assertEqual(ticker.get_pool_transactions.await_args_list[1].args, (pool, 10))
        self.assertEqual(manager.notify.await_args_list[0].args[0], 'kline')
        self.assertEqual(manager.notify.await_args_list[2].args[0], 'kline')
        second_kline_payload = manager.notify.await_args_list[2].args[1]
        self.assertEqual(second_kline_payload['1min'][0]['points'][0]['timestamp'], 1_800_000_000_000)


if __name__ == '__main__':
    unittest.main()
