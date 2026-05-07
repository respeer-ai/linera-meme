import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.settled_trade_projection_repo import SettledTradeProjectionRepository  # noqa: E402


class SettledTradeProjectionRepositoryTest(unittest.TestCase):
    class FakeCursor:
        def __init__(self):
            self.executed = []
            self.rows = []
            self.responses = []
            self.pool_rows = [{
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
            }]
            self.last_sql = ''
            self.last_params = ()

        def execute(self, sql, params=()):
            self.executed.append((sql, params))
            self.last_sql = sql
            self.last_params = params

        def fetchall(self):
            if 'FROM pools' in self.last_sql:
                if 'WHERE token_0 = %s' in self.last_sql and 'AND token_1 = %s' in self.last_sql:
                    return [
                        row for row in self.pool_rows
                        if row['token_0'] == self.last_params[0] and row['token_1'] == self.last_params[1]
                    ]
                if 'WHERE pool_id = %s' in self.last_sql:
                    return [
                        row for row in self.pool_rows
                        if int(row['pool_id']) == int(self.last_params[0])
                    ]
            if self.responses:
                return list(self.responses.pop(0))
            return list(self.rows)

        def fetchone(self):
            rows = self.fetchall()
            if not rows:
                return None
            return rows[0]

    class FakeDb:
        def __init__(self):
            self.cursor_dict = SettledTradeProjectionRepositoryTest.FakeCursor()
            self.calls = []
            self.pools_table = 'pools'
            self.current_now_ms = 10_000

        def ensure_fresh_read_connection(self):
            self.calls.append('ensure_fresh_read_connection')

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
                'from_account': 'chain-user:owner-user',
                'amount_0_in': None,
                'amount_0_out': '300',
                'amount_1_in': '25',
                'amount_1_out': None,
                'amount_in': '25',
                'amount_out': '300',
                'event_payload_json': {},
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
        self.assertEqual(rows[0]['from_account'], 'chain-user:owner-user')
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
                'from_account': 'c:o',
                'amount_0_in': None,
                'amount_0_out': '10',
                'amount_1_in': '20',
                'amount_1_out': None,
                'amount_in': '20',
                'amount_out': '10',
                'event_payload_json': {},
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
                'from_account': 'c:o',
                'amount_0_in': '6',
                'amount_0_out': None,
                'amount_1_in': None,
                'amount_1_out': '18',
                'amount_in': '6',
                'amount_out': '18',
                'event_payload_json': {},
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

    def test_trade_queries_join_against_prefixed_pool_application(self):
        db = self.FakeDb()
        db.cursor_dict.pool_rows = [{
            'pool_id': 7,
            'pool_application': 'chain-a:0xpool-app',
            'token_0': 'AAA',
            'token_1': 'BBB',
        }]
        db.cursor_dict.rows = [
            {
                'pool_id': 7,
                'pool_application': 'chain-a:0xpool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'settled_trade_id': 'trade-1',
                'transaction_id': 11,
                'trade_time_ms': 1200,
                'side': 'buy_token_0',
                'from_account': 'chain-user:owner-user',
                'amount_0_in': None,
                'amount_0_out': '300',
                'amount_1_in': '25',
                'amount_1_out': None,
                'amount_in': '25',
                'amount_out': '300',
                'event_payload_json': {},
            }
        ]
        repository = SettledTradeProjectionRepository(db)

        rows = repository.get_transactions(
            token_0='AAA',
            token_1='BBB',
            start_at=1000,
            end_at=2000,
        )

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['pool_application'], 'chain-a:0xpool-app')

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
                    'from_account': 'c:o',
                    'amount_0_in': None,
                    'amount_0_out': '10',
                    'amount_1_in': '20',
                    'amount_1_out': None,
                    'amount_in': '20',
                    'amount_out': '10',
                    'event_payload_json': {},
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

    def test_settled_trade_projection_uses_projection_pool_identity_boundary(self):
        db = self.FakeDb()

        class FakePoolIdentityProjectionRepository:
            def __init__(self):
                self.calls = []

            def resolve_for_tokens(self, token_0, token_1):
                self.calls.append(('resolve_for_tokens', token_0, token_1))
                return (7, 'chain-a:pool-app', token_0, token_1, False)

            def resolve_for_read(self, token_0, token_1, *, pool_id=None, pool_application=None):
                self.calls.append(('resolve_for_read', token_0, token_1, pool_id, pool_application))
                return (7, pool_application or 'chain-a:pool-app', token_0, token_1, False)

        pool_identity_repo = FakePoolIdentityProjectionRepository()
        db.cursor_dict.responses = [
            [],
            [],
            [],
        ]
        repository = SettledTradeProjectionRepository(
            db,
            pool_identity_projection_repo=pool_identity_repo,
        )

        repository.get_transactions(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
        )
        repository.get_candles(
            token_0='AAA',
            token_1='BBB',
            start_at=0,
            end_at=59_999,
            interval='1min',
        )

        self.assertEqual(
            pool_identity_repo.calls,
            [
                ('resolve_for_tokens', 'AAA', 'BBB'),
                ('resolve_for_read', 'AAA', 'BBB', None, None),
            ],
        )
