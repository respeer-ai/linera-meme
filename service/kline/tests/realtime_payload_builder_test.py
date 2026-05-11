import sys
import types
import unittest
from unittest.mock import Mock
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from realtime.market_data_event import MarketDataEvent  # noqa: E402
from realtime.market_data_payload_builder import MarketDataPayloadBuilder  # noqa: E402
from websocket_candle_reader import WebsocketCandleReader  # noqa: E402


POOL_OWNER = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
POOL_CHAIN = 'chain'
POOL_APPLICATION = f'{POOL_OWNER}@{POOL_CHAIN}'


class FakeHistoryRepository:
    def __init__(self):
        self.points = {}
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


class FakePoolCatalogRepository:
    def __init__(self, pools):
        self.pools = pools

    def list_current_pool_views(self):
        return list(self.pools)


def make_pool(pool_id=7, token_0='AAA', token_1='BBB'):
    return types.SimpleNamespace(
        pool_id=pool_id,
        token_0=token_0,
        token_1=token_1,
        pool_application=types.SimpleNamespace(chain_id=POOL_CHAIN, owner=POOL_OWNER),
    )


class MarketDataPayloadBuilderTest(unittest.TestCase):
    def test_websocket_candle_reader_exposes_get_points_for_realtime_builder(self):
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

    def test_builds_incremental_payload_from_settled_trade_event(self):
        db = FakeHistoryRepository()
        candle_reader = FakeCandleReader(db)
        pool = make_pool()
        db.pool_histories[(7, POOL_APPLICATION)] = [
            {
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'token_reversed': False,
                'created_at': 1_800_000_001_000,
            },
        ]
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
        db.points[(7, True, '1min', 1_800_000_000_000)] = {
            'timestamp': 1_800_000_000_000,
            'token_0': 'BBB',
            'token_1': 'AAA',
            'bucket_start_ms': 1_800_000_000_000,
            'bucket_end_ms': 1_800_000_059_999,
            'is_final': False,
            'open': 0.5,
            'high': 0.5,
            'low': 0.25,
            'close': 0.25,
            'base_volume': 35.0,
            'quote_volume': 14.0,
        }
        builder = MarketDataPayloadBuilder(
            pool_catalog_repository=FakePoolCatalogRepository([pool]),
            candle_reader=candle_reader,
            transaction_history_repository=db,
            now_ms=lambda: 1_800_000_030_000,
        )

        payload = builder.build([
            MarketDataEvent(
                event_type=MarketDataEvent.TYPE_SETTLED_TRADE,
                pool_application=POOL_APPLICATION,
                transaction_id=10,
                event_time_ms=1_800_000_001_000,
            )
        ])

        self.assertEqual(payload['transactions'][0]['transactions'][0]['transaction_id'], 10)
        self.assertEqual(
            payload['kline']['1min'][0]['points'][0],
            db.points[(7, False, '1min', 1_800_000_000_000)],
        )
        self.assertEqual(
            payload['kline']['1min'][1]['token_0'],
            'BBB',
        )
        self.assertEqual(
            payload['kline']['1min'][1]['token_1'],
            'AAA',
        )
        self.assertEqual(payload['positions'], {
            'events': [{
                'pool_application': POOL_APPLICATION,
                'pool_id': 7,
                'owners': [],
                'event_types': ['settled_trade'],
                'updated_at': None,
            }],
        })

    def test_ignores_non_trade_transactions_for_kline(self):
        db = FakeHistoryRepository()
        pool = make_pool()
        db.pool_histories[(7, POOL_APPLICATION)] = [
            {
                'transaction_id': 100,
                'transaction_type': 'AddLiquidity',
                'created_at': 1_800_000_001_000,
            },
        ]
        builder = MarketDataPayloadBuilder(
            pool_catalog_repository=FakePoolCatalogRepository([pool]),
            candle_reader=FakeCandleReader(db),
            transaction_history_repository=db,
        )

        payload = builder.build([
            MarketDataEvent(
                event_type=MarketDataEvent.TYPE_SETTLED_TRADE,
                pool_application=POOL_APPLICATION,
                transaction_id=100,
            )
        ])

        self.assertEqual(payload['kline'], {})

    def test_builds_rollover_payload_only_after_bucket_finality_event(self):
        db = FakeHistoryRepository()
        candle_reader = FakeCandleReader(db)
        pool = make_pool()
        db.points[(7, False, '1min', 1_800_000_060_000)] = {
            'timestamp': 1_800_000_060_000,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'bucket_start_ms': 1_800_000_060_000,
            'bucket_end_ms': 1_800_000_119_999,
            'is_final': True,
            'open': 3.0,
            'high': 3.0,
            'low': 3.0,
            'close': 3.0,
            'base_volume': 0.0,
            'quote_volume': 0.0,
        }
        builder = MarketDataPayloadBuilder(
            pool_catalog_repository=FakePoolCatalogRepository([pool]),
            candle_reader=candle_reader,
            transaction_history_repository=db,
            now_ms=lambda: 1_800_000_130_000,
        )
        builder.last_emitted_bucket_starts[(7, POOL_APPLICATION, 'AAA', 'BBB', '1min')] = 1_800_000_000_000

        payload = builder.build([
            MarketDataEvent(
                event_type=MarketDataEvent.TYPE_CANDLE_FINALIZED,
                pool_application=POOL_APPLICATION,
                event_time_ms=1_800_000_060_000,
            )
        ])

        self.assertEqual(payload['kline']['1min'][0]['start_at'], 1_800_000_060_000)
        self.assertEqual(payload['kline']['1min'][0]['points'][0]['base_volume'], 0.0)


if __name__ == '__main__':
    unittest.main()
