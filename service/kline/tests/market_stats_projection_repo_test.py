import sys
import unittest
from pathlib import Path
from decimal import Decimal


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.market_stats_projection_repo import MarketStatsProjectionRepository  # noqa: E402


class MarketStatsProjectionRepositoryTest(unittest.TestCase):
    class FakeCursor:
        def __init__(self):
            self.executed = []
            self.rows = []

        def execute(self, sql, params=()):
            self.executed.append((sql, params))

        def fetchall(self):
            return list(self.rows)

    class FakeDb:
        def __init__(self):
            self.cursor_dict = MarketStatsProjectionRepositoryTest.FakeCursor()
            self.pools_table = 'pools'
            self.current_now_ms = 2_000_000

        def ensure_fresh_read_connection(self):
            return None

        def now_ms(self):
            return self.current_now_ms

    def test_get_ticker_aggregates_token_stats_from_settled_trades(self):
        db = self.FakeDb()
        db.cursor_dict.rows = [
            {
                'pool_id': 7,
                'pool_application': 'chain:pool-a',
                'token_0': 'AAA',
                'token_1': 'TLINERA',
                'trade_time_ms': 1_000,
                'side': 'buy_token_0',
                'amount_in': '20000000000000000000',
                'amount_out': '10000000000000000000',
            },
            {
                'pool_id': 7,
                'pool_application': 'chain:pool-a',
                'token_0': 'AAA',
                'token_1': 'TLINERA',
                'trade_time_ms': 2_000,
                'side': 'sell_token_0',
                'amount_in': '5000000000000000000',
                'amount_out': '15000000000000000000',
            },
        ]
        repository = MarketStatsProjectionRepository(db)

        rows = repository.get_ticker(interval='all')

        aaa_row = next(row for row in rows if row['token'] == 'AAA')
        self.assertEqual(aaa_row['tx_count'], 2)
        self.assertEqual(aaa_row['high'], 3.0)
        self.assertEqual(aaa_row['low'], 2.0)
        self.assertEqual(aaa_row['price_now'], 3.0)
        self.assertEqual(aaa_row['price_start'], 2.0)
        self.assertEqual(len(rows), 1)

    def test_get_pool_stats_aggregates_pool_rows_from_settled_trades(self):
        db = self.FakeDb()
        db.cursor_dict.rows = [
            {
                'pool_id': 7,
                'pool_application': 'chain:pool-a',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'trade_time_ms': 1_000,
                'side': 'buy_token_0',
                'amount_in': '20000000000000000000',
                'amount_out': '10000000000000000000',
            },
            {
                'pool_id': 7,
                'pool_application': 'chain:pool-a',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'trade_time_ms': 2_000,
                'side': 'sell_token_0',
                'amount_in': '5000000000000000000',
                'amount_out': '15000000000000000000',
            },
        ]
        repository = MarketStatsProjectionRepository(db)

        rows = repository.get_pool_stats(interval='all')

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['pool_id'], 7)
        self.assertEqual(rows[0]['high'], 3.0)
        self.assertEqual(rows[0]['low'], 2.0)
        self.assertEqual(rows[0]['price_now'], 3.0)
        self.assertEqual(rows[0]['price_start'], 2.0)
        self.assertEqual(rows[0]['tx_count'], 2)
        self.assertEqual(rows[0]['volume'], 35.0)

    def test_get_protocol_stats_uses_settled_trades_and_live_pool_reserves(self):
        db = self.FakeDb()
        db.current_now_ms = 200_000_000
        db.cursor_dict.rows = [
            {
                'pool_id': 7,
                'pool_application': 'chain:pool-a',
                'token_0': 'AAA',
                'token_1': 'TLINERA',
                'trade_time_ms': 150_000_000,
                'side': 'buy_token_0',
                'amount_in': '20000000000000000000',
                'amount_out': '10000000000000000000',
            },
        ]
        repository = MarketStatsProjectionRepository(db)
        pools = [
            type(
                'Pool',
                (),
                {
                    'token_0': 'AAA',
                    'token_1': 'TLINERA',
                    'reserve_0': Decimal('100'),
                    'reserve_1': Decimal('200'),
                },
            )(),
        ]

        stats = repository.get_protocol_stats(pools=pools)

        self.assertEqual(stats['pool_count'], 1)
        self.assertEqual(stats['tx_count'], 1)
        self.assertEqual(stats['fees'], 0.06)
        self.assertGreaterEqual(stats['tvl'], 0.0)


if __name__ == '__main__':
    unittest.main()
