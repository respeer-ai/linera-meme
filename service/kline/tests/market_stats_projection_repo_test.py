import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.market_stats_projection_repo import MarketStatsProjectionRepository  # noqa: E402


class MarketStatsProjectionRepositoryTest(unittest.TestCase):
    class FakeMetadataResolver:
        def __init__(self, metadata):
            self.metadata = metadata

        def metadata_by_pool_application(self):
            return dict(self.metadata)

    def test_get_protocol_stats_uses_projection_pool_rows(self):
        class FakeDb:
            def now_ms(self):
                return 2_000_000

            def ensure_fresh_read_connection(self):
                return None

            class Cursor:
                def __init__(self):
                    self.rows = []

                def execute(self, _sql, _params=()):
                    return None

                def fetchall(self):
                    return list(self.rows)

            cursor_dict = Cursor()
            pools_table = 'pools'

        db = FakeDb()
        repo = MarketStatsProjectionRepository(db)
        repo._load_settled_trade_rows = lambda start_at=None, end_at=None: [
            {
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'AAA',
                'token_1': 'TLINERA',
                'trade_time_ms': 1_500_000,
                'side': 'buy_token_0',
                'amount_in': '3000000000000000000',
                'amount_out': '1000000000000000000',
            }
        ] if start_at and start_at >= 1_000_000 else []
        stats = repo.get_protocol_stats(
            pools=[
                {
                    'pool_id': 7,
                    'pool_application': 'chain-a:pool-app',
                    'token_0': 'AAA',
                    'token_1': 'TLINERA',
                    'current_reserve_0': '2',
                    'current_reserve_1': '5',
                }
            ]
        )

        self.assertEqual(stats['pool_count'], 1)
        self.assertEqual(stats['tvl'], 10.0)
        self.assertEqual(stats['volume'], 0.0)

    def test_get_protocol_stats_values_meme_meme_pool_through_reserve_graph(self):
        class FakeDb:
            def now_ms(self):
                return 2_000_000

            def ensure_fresh_read_connection(self):
                return None

            class Cursor:
                def execute(self, _sql, _params=()):
                    return None

                def fetchall(self):
                    return []

                def close(self):
                    return None

            cursor_dict = Cursor()

            def fresh_cursor(self, dictionary=False):
                return self.Cursor()

        repo = MarketStatsProjectionRepository(
            FakeDb(),
            metadata_resolver=self.FakeMetadataResolver({}),
        )

        stats = repo.get_protocol_stats(
            pools=[
                {
                    'pool_id': 7,
                    'pool_application': 'chain-a:pool-aaa-native',
                    'token_0': 'AAA',
                    'token_1': 'TLINERA',
                    'current_reserve_0': '2',
                    'current_reserve_1': '5',
                },
                {
                    'pool_id': 8,
                    'pool_application': 'chain-a:pool-bbb-aaa',
                    'token_0': 'BBB',
                    'token_1': 'AAA',
                    'current_reserve_0': '10',
                    'current_reserve_1': '4',
                },
            ]
        )

        self.assertEqual(stats['tvl'], 30.0)

    def test_get_protocol_stats_values_fees_by_input_token_amount_through_reserve_graph(self):
        class FakeDb:
            def now_ms(self):
                return 100_000_000

            def ensure_fresh_read_connection(self):
                return None

        repo = MarketStatsProjectionRepository(
            FakeDb(),
            metadata_resolver=self.FakeMetadataResolver({}),
        )
        repo._load_settled_trade_rows = lambda start_at=None, end_at=None: [
            {
                'pool_id': 8,
                'pool_application': 'chain-a:pool-bbb-aaa',
                'token_0': 'BBB',
                'token_1': 'AAA',
                'trade_time_ms': 1_500_000,
                'side': 'sell_token_0',
                'amount_in': '10000000000000000000',
                'amount_out': '4000000000000000000',
            }
        ] if end_at == repo._now_ms() else []

        stats = repo.get_protocol_stats(
            pools=[
                {
                    'pool_id': 7,
                    'pool_application': 'chain-a:pool-aaa-native',
                    'token_0': 'AAA',
                    'token_1': 'TLINERA',
                    'current_reserve_0': '2',
                    'current_reserve_1': '5',
                },
                {
                    'pool_id': 8,
                    'pool_application': 'chain-a:pool-bbb-aaa',
                    'token_0': 'BBB',
                    'token_1': 'AAA',
                    'current_reserve_0': '10',
                    'current_reserve_1': '4',
                },
            ]
        )

        self.assertEqual(stats['fees'], 0.03)

    def test_load_settled_trade_rows_attaches_projection_metadata_without_joining_pools(self):
        class FakeDb:
            def __init__(self):
                self.executed = []

            def ensure_fresh_read_connection(self):
                return None

            class Cursor:
                def __init__(self, outer):
                    self.outer = outer

                def execute(self, sql, params=()):
                    self.outer.executed.append((sql, params))

                def fetchall(self):
                    return [
                        {
                            'pool_application': 'chain-a:0xpool-app',
                            'trade_time_ms': 1_500_000,
                            'side': 'buy_token_0',
                            'amount_in': '3000000000000000000',
                            'amount_out': '1000000000000000000',
                        }
                    ]

                def close(self):
                    return None

            @property
            def cursor_dict(self):
                return self.Cursor(self)

            def fresh_cursor(self, dictionary=False):
                return self.Cursor(self)

        db = FakeDb()
        repo = MarketStatsProjectionRepository(
            db,
            metadata_resolver=self.FakeMetadataResolver({
                'chain-a:0xpool-app': {'pool_id': 7, 'token_0': 'AAA', 'token_1': 'TLINERA'},
            }),
        )

        rows = repo._load_settled_trade_rows(start_at=1_000, end_at=2_000)

        self.assertEqual(rows[0]['pool_application'], 'chain-a:0xpool-app')
        self.assertEqual(rows[0]['pool_id'], 7)
        self.assertEqual(rows[0]['token_0'], 'AAA')
        self.assertNotIn('JOIN', db.executed[0][0])

    def test_get_pool_stats_exposes_pool_application_for_protocol_identity_matching(self):
        class FakeDb:
            def now_ms(self):
                return 2_000_000

            def ensure_fresh_read_connection(self):
                return None

            class Cursor:
                def execute(self, _sql, _params=()):
                    return None

                def fetchall(self):
                    return [
                        {
                            'pool_application': 'chain-a:0xpool-app',
                            'trade_time_ms': 1_500_000,
                            'side': 'buy_token_0',
                            'amount_in': '3000000000000000000',
                            'amount_out': '1000000000000000000',
                        }
                    ]

                def close(self):
                    return None

            cursor_dict = Cursor()

            def fresh_cursor(self, dictionary=False):
                return self.Cursor()

        repo = MarketStatsProjectionRepository(
            FakeDb(),
            metadata_resolver=self.FakeMetadataResolver({
                'chain-a:0xpool-app': {'pool_id': 7, 'token_0': 'AAA', 'token_1': 'TLINERA'},
            }),
        )

        stats = repo.get_pool_stats(interval='1d')

        self.assertEqual(stats[0]['pool_application'], 'chain-a:0xpool-app')
        self.assertEqual(stats[0]['pool_id'], 7)

    def test_load_settled_trade_rows_supports_prefixed_projection_pool_application(self):
        class FakeDb:
            def ensure_fresh_read_connection(self):
                return None

            class Cursor:
                def execute(self, _sql, _params=()):
                    return None

                def fetchall(self):
                    return [
                        {
                            'pool_application': 'chain-a:0xpool-app',
                            'trade_time_ms': 1_500_000,
                            'side': 'buy_token_0',
                            'amount_in': '3000000000000000000',
                            'amount_out': '1000000000000000000',
                        }
                    ]

                def close(self):
                    return None

            cursor_dict = Cursor()

            def fresh_cursor(self, dictionary=False):
                return self.Cursor()

        repo = MarketStatsProjectionRepository(
            FakeDb(),
            metadata_resolver=self.FakeMetadataResolver({
                'chain-a:0xpool-app': {'pool_id': 7, 'token_0': 'AAA', 'token_1': 'TLINERA'},
            }),
        )

        rows = repo._load_settled_trade_rows()

        self.assertEqual(rows[0]['pool_application'], 'chain-a:0xpool-app')
        self.assertEqual(rows[0]['pool_id'], 7)

    def test_load_settled_trade_rows_skips_projection_metadata_without_pool_id(self):
        class FakeDb:
            def ensure_fresh_read_connection(self):
                return None

            class Cursor:
                def execute(self, _sql, _params=()):
                    return None

                def fetchall(self):
                    return [
                        {
                            'pool_application': 'chain-a:pool-app',
                            'trade_time_ms': 1_500_000,
                            'side': 'buy_token_0',
                            'amount_in': '3000000000000000000',
                            'amount_out': '1000000000000000000',
                        }
                    ]

                def close(self):
                    return None

            cursor_dict = Cursor()

            def fresh_cursor(self, dictionary=False):
                return self.Cursor()

        repo = MarketStatsProjectionRepository(
            FakeDb(),
            metadata_resolver=self.FakeMetadataResolver({
                'chain-a:pool-app': {'pool_id': None, 'token_0': 'AAA', 'token_1': 'TLINERA'},
            }),
        )

        self.assertEqual(repo._load_settled_trade_rows(), [])


if __name__ == '__main__':
    unittest.main()
