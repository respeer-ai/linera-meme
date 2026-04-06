import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from candle_schema import (  # noqa: E402
    CandleBucketKey,
    CandleState,
    CandleUpdate,
    apply_candle_update,
    build_candle_bucket_key,
    get_interval_bucket_ms,
)


class CandleSchemaContractTest(unittest.TestCase):
    def test_maps_supported_intervals_to_bucket_sizes(self):
        self.assertEqual(get_interval_bucket_ms('1min'), 60_000)
        self.assertEqual(get_interval_bucket_ms('5min'), 300_000)
        self.assertEqual(get_interval_bucket_ms('10min'), 600_000)
        self.assertEqual(get_interval_bucket_ms('1h'), 3_600_000)

    def test_builds_bucket_key_using_pool_reverse_interval_and_bucket_start(self):
        self.assertEqual(
            build_candle_bucket_key(
                pool_id=1000,
                token_reversed=False,
                interval='5min',
                created_at_ms=1_775_465_307_782,
            ),
            CandleBucketKey(
                pool_id=1000,
                token_reversed=False,
                interval='5min',
                bucket_start_ms=1_775_465_100_000,
            ),
        )

    def test_creates_first_candle_from_first_trade_in_bucket(self):
        update = CandleUpdate(
            transaction_id=10,
            created_at_ms=1_775_465_073_302,
            price=0.00703921,
            volume=8.99,
        )

        candle = apply_candle_update(existing=None, update=update)

        self.assertEqual(
            candle,
            CandleState(
                open=0.00703921,
                high=0.00703921,
                low=0.00703921,
                close=0.00703921,
                volume=8.99,
                trade_count=1,
                first_trade_id=10,
                last_trade_id=10,
                first_trade_at_ms=1_775_465_073_302,
                last_trade_at_ms=1_775_465_073_302,
            ),
        )

    def test_updates_existing_candle_with_later_trade(self):
        existing = CandleState(
            open=0.00703921,
            high=0.00703921,
            low=0.00703921,
            close=0.00703921,
            volume=8.99,
            trade_count=1,
            first_trade_id=10,
            last_trade_id=10,
            first_trade_at_ms=1_775_465_073_302,
            last_trade_at_ms=1_775_465_073_302,
        )
        update = CandleUpdate(
            transaction_id=11,
            created_at_ms=1_775_465_085_099,
            price=0.00703925,
            volume=693.79,
        )

        candle = apply_candle_update(existing=existing, update=update)

        self.assertEqual(candle.open, 0.00703921)
        self.assertEqual(candle.high, 0.00703925)
        self.assertEqual(candle.low, 0.00703921)
        self.assertEqual(candle.close, 0.00703925)
        self.assertEqual(candle.volume, 702.78)
        self.assertEqual(candle.trade_count, 2)
        self.assertEqual(candle.first_trade_id, 10)
        self.assertEqual(candle.last_trade_id, 11)

    def test_ignores_duplicate_trade_replay_for_idempotency(self):
        existing = CandleState(
            open=0.00703921,
            high=0.00703925,
            low=0.00703921,
            close=0.00703925,
            volume=702.78,
            trade_count=2,
            first_trade_id=10,
            last_trade_id=11,
            first_trade_at_ms=1_775_465_073_302,
            last_trade_at_ms=1_775_465_085_099,
        )
        replay = CandleUpdate(
            transaction_id=11,
            created_at_ms=1_775_465_085_099,
            price=0.00703925,
            volume=693.79,
        )

        candle = apply_candle_update(existing=existing, update=replay)

        self.assertEqual(candle, existing)


if __name__ == '__main__':
    unittest.main()
