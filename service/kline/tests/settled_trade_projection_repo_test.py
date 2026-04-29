import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.projection_repo import ProjectionRepository  # noqa: E402
from storage.mysql.settled_trade_projection_repo import SettledTradeProjectionRepository  # noqa: E402


class SettledTradeProjectionRepositoryTest(unittest.TestCase):
    class FakeCursor:
        def __init__(self):
            self.executed = []
            self.rows = []
            self.responses = []

        def execute(self, sql, params=()):
            self.executed.append((sql, params))

        def fetchall(self):
            if self.responses:
                return list(self.responses.pop(0))
            return list(self.rows)

    class FakeDb:
        def __init__(self):
            self.cursor_dict = SettledTradeProjectionRepositoryTest.FakeCursor()
            self.calls = []
            self.pools_table = 'pools'
            self.current_now_ms = 10_000

        def ensure_fresh_read_connection(self):
            self.calls.append('ensure_fresh_read_connection')

        def get_pool_identity(self, token_0, token_1):
            self.calls.append(('get_pool_identity', token_0, token_1))
            return (7, 'chain-a:pool-app', token_0, token_1, False)

        def resolve_pool_identity_for_read(self, token_0, token_1, *, pool_id=None, pool_application=None):
            self.calls.append(('resolve_pool_identity_for_read', token_0, token_1, pool_id, pool_application))
            return (
                7,
                pool_application or 'chain-a:pool-app',
                token_0,
                token_1,
                False,
            )

        def now_ms(self):
            return self.current_now_ms

        def get_transactions(self, **kwargs):
            self.calls.append(('legacy_get_transactions', dict(kwargs)))
            return [{'transaction_id': 99}]

        def get_transactions_information(self, **kwargs):
            self.calls.append(('legacy_get_transactions_information', dict(kwargs)))
            return {'count': 9}

        def get_kline(self, **kwargs):
            self.calls.append(('legacy_get_kline', dict(kwargs)))
            return (7, 'chain-a:pool-app', kwargs['token_0'], kwargs['token_1'], [{'close': '9'}])

        def get_kline_information(self, **kwargs):
            self.calls.append(('legacy_get_kline_information', dict(kwargs)))
            return {'count': 8}

    def test_get_transactions_builds_forward_and_reverse_rows_for_unfiltered_queries(self):
        db = self.FakeDb()
        db.cursor_dict.rows = [
            {
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'settled_trade_id': 'trade-1',
                'transaction_id': 11,
                'trade_time_ms': 1200,
                'side': 'buy_token_0',
                'amount_in': '25',
                'amount_out': '300',
                'event_payload_json': json.dumps({
                    'transaction': {
                        'from': {'chain_id': 'chain-user', 'owner': 'owner-user'},
                        'amount_0_in': None,
                        'amount_0_out': '300',
                        'amount_1_in': '25',
                        'amount_1_out': None,
                        'liquidity': None,
                    }
                }),
            }
        ]
        repository = SettledTradeProjectionRepository(db)

        rows = repository.get_transactions(
            token_0=None,
            token_1=None,
            start_at=1000,
            end_at=2000,
        )

        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['transaction_type'], 'BuyToken0')
        self.assertEqual(rows[0]['direction'], 'Buy')
        self.assertEqual(rows[0]['volume'], 300.0)
        self.assertAlmostEqual(rows[0]['price'], 25 / 300)
        self.assertEqual(rows[1]['direction'], 'Sell')
        self.assertEqual(rows[1]['volume'], 25.0)
        self.assertAlmostEqual(rows[1]['price'], 300 / 25)

    def test_get_candles_aggregates_points_from_settled_trades(self):
        db = self.FakeDb()
        db.cursor_dict.rows = [
            {
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'settled_trade_id': 'trade-1',
                'transaction_id': 10,
                'trade_time_ms': 1_000,
                'side': 'buy_token_0',
                'amount_in': '20',
                'amount_out': '10',
                'event_payload_json': json.dumps({'transaction': {'from': {'chain_id': 'c', 'owner': 'o'}}}),
            },
            {
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'settled_trade_id': 'trade-2',
                'transaction_id': 11,
                'trade_time_ms': 20_000,
                'side': 'sell_token_0',
                'amount_in': '6',
                'amount_out': '18',
                'event_payload_json': json.dumps({'transaction': {'from': {'chain_id': 'c', 'owner': 'o'}}}),
            },
        ]
        repository = SettledTradeProjectionRepository(db)

        payload = repository.get_candles(
            token_0='AAA',
            token_1='BBB',
            start_at=0,
            end_at=59_999,
            interval='1min',
        )

        self.assertEqual(payload[0], 7)
        self.assertEqual(payload[1], 'chain-a:pool-app')
        self.assertEqual(len(payload[4]), 1)
        point = payload[4][0]
        self.assertEqual(point['timestamp'], 0)
        self.assertEqual(point['open'], 2.0)
        self.assertEqual(point['close'], 3.0)
        self.assertEqual(point['high'], 3.0)
        self.assertEqual(point['low'], 2.0)
        self.assertEqual(point['base_volume'], 16.0)
        self.assertEqual(point['quote_volume'], 38.0)

    def test_get_candles_builds_empty_finalized_buckets_from_previous_close(self):
        db = self.FakeDb()
        db.current_now_ms = 180_000
        db.cursor_dict.responses = [
            [],
            [
                {
                    'pool_id': 7,
                    'pool_application': 'chain-a:pool-app',
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'settled_trade_id': 'trade-prev',
                    'transaction_id': 9,
                    'trade_time_ms': 59_000,
                    'side': 'buy_token_0',
                    'amount_in': '20',
                    'amount_out': '10',
                    'event_payload_json': json.dumps({'transaction': {'from': {'chain_id': 'c', 'owner': 'o'}}}),
                }
            ],
        ]
        repository = SettledTradeProjectionRepository(db)

        payload = repository.get_candles(
            token_0='AAA',
            token_1='BBB',
            start_at=60_000,
            end_at=179_999,
            interval='1min',
        )

        self.assertEqual(len(payload[4]), 2)
        self.assertEqual(payload[4][0]['timestamp'], 60_000)
        self.assertEqual(payload[4][0]['open'], 2.0)
        self.assertEqual(payload[4][0]['base_volume'], 0.0)
        self.assertEqual(payload[4][1]['timestamp'], 120_000)

    def test_settled_projection_returns_empty_payloads_without_falling_back_to_legacy(self):
        db = self.FakeDb()
        db.cursor_dict.responses = [
            [],
            [],
            [],
            [],
        ]
        repository = SettledTradeProjectionRepository(db)

        transactions = repository.get_transactions(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
        )
        transaction_info = repository.get_transactions_information(
            token_0='AAA',
            token_1='BBB',
        )
        candles = repository.get_candles(
            token_0='AAA',
            token_1='BBB',
            start_at=0,
            end_at=59_999,
            interval='1min',
        )
        candle_info = repository.get_candles_information(
            token_0='AAA',
            token_1='BBB',
            interval='1min',
        )

        self.assertEqual(transactions, [])
        self.assertEqual(
            transaction_info,
            {'count': 0, 'timestamp_begin': None, 'timestamp_end': None},
        )
        self.assertEqual(candles[4], [])
        self.assertEqual(
            candle_info,
            {'count': 0, 'timestamp_begin': None, 'timestamp_end': None},
        )

    def test_projection_repository_falls_back_to_legacy_when_settled_projection_is_unavailable(self):
        db = self.FakeDb()

        class MissingSettledTradeProjectionRepository:
            def get_transactions(self, **_kwargs):
                return None

            def get_transactions_information(self, **_kwargs):
                return None

            def get_candles(self, **_kwargs):
                return None

            def get_candles_information(self, **_kwargs):
                return None

        repository = ProjectionRepository(
            db,
            settled_trade_projection_repo=MissingSettledTradeProjectionRepository(),
        )

        transactions = repository.get_transactions(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
        )
        info = repository.get_transactions_information(
            token_0='AAA',
            token_1='BBB',
        )
        candles = repository.get_candles(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
            interval='1min',
        )

        self.assertEqual(transactions, [{'transaction_id': 99}])
        self.assertEqual(info, {'count': 9})
        self.assertEqual(candles[4], [{'close': '9'}])

    def test_projection_repository_keeps_empty_projection_results_without_legacy_fallback(self):
        db = self.FakeDb()
        repository = ProjectionRepository(
            db,
            settled_trade_projection_repo=SettledTradeProjectionRepository(db),
        )

        db.cursor_dict.responses = [
            [],
            [],
            [],
            [],
        ]

        transactions = repository.get_transactions(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
        )
        info = repository.get_transactions_information(
            token_0='AAA',
            token_1='BBB',
        )
        candles = repository.get_candles(
            token_0='AAA',
            token_1='BBB',
            start_at=0,
            end_at=59_999,
            interval='1min',
        )
        candle_info = repository.get_candles_information(
            token_0='AAA',
            token_1='BBB',
            interval='1min',
        )

        self.assertEqual(transactions, [])
        self.assertEqual(info, {'count': 0, 'timestamp_begin': None, 'timestamp_end': None})
        self.assertEqual(candles[4], [])
        self.assertEqual(candle_info, {'count': 0, 'timestamp_begin': None, 'timestamp_end': None})
        self.assertFalse(any(call[0].startswith('legacy_') for call in db.calls))
