import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


swap_stub = types.ModuleType('swap')
swap_stub.Pool = object
swap_stub.Transaction = object
sys.modules.setdefault('swap', swap_stub)

from ticker import Ticker  # noqa: E402


class FakeDb:
    def __init__(self):
        self.points = {}

    def get_candle_point(self, pool_id, token_reversed, interval, bucket_start_ms):
        return self.points.get((pool_id, token_reversed, interval, bucket_start_ms))


class TickerIncrementalPayloadTest(unittest.TestCase):
    def test_builds_incremental_payload_with_only_changed_candles(self):
        db = FakeDb()
        db.points[(7, False, '5min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'open': 2.0,
            'high': 3.0,
            'low': 2.0,
            'close': 3.0,
            'volume': 14.0,
        }
        db.points[(7, True, '5min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'open': 0.5,
            'high': 0.5,
            'low': 0.33,
            'close': 0.33,
            'volume': 32.0,
        }
        ticker = Ticker(manager=None, swap=None, db=db)
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
                'points': [db.points[(7, False, '5min', 1_800_000_000_000)]],
            },
            {
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


if __name__ == '__main__':
    unittest.main()
