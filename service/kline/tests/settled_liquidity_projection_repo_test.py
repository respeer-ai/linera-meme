import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.settled_liquidity_projection_repo import SettledLiquidityProjectionRepository  # noqa: E402
from storage.mysql.settled_pool_history_projection_repo import SettledPoolHistoryProjectionRepository  # noqa: E402


class SettledLiquidityProjectionRepositoryTest(unittest.TestCase):
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
            self.cursor_dict = SettledLiquidityProjectionRepositoryTest.FakeCursor()
            self.calls = []
            self.pools_table = 'pools'

        def ensure_fresh_read_connection(self):
            self.calls.append('ensure_fresh_read_connection')

        def get_positions(self, **kwargs):
            self.calls.append(('legacy_get_positions', dict(kwargs)))
            return [{'pool_id': 99}]

        def get_position_liquidity_history(self, **kwargs):
            self.calls.append(('legacy_get_position_liquidity_history', dict(kwargs)))
            return [{'transaction_id': 98}]

        def get_pool_transaction_history(self, **kwargs):
            self.calls.append(('legacy_get_pool_transaction_history', dict(kwargs)))
            return [{'transaction_id': 97}]

    def test_get_positions_aggregates_active_and_closed_positions(self):
        db = self.FakeDb()
        db.cursor_dict.rows = [
            {
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'owner': 'owner-a@chain-a',
                'change_type': 'add_liquidity',
                'liquidity_delta': '10',
                'event_time_ms': 1000,
            },
            {
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'owner': 'owner-a@chain-a',
                'change_type': 'remove_liquidity',
                'liquidity_delta': '4',
                'event_time_ms': 2000,
            },
            {
                'pool_id': 8,
                'pool_application': 'chain-b:pool-app-2',
                'token_0': 'CCC',
                'token_1': 'TLINERA',
                'owner': 'owner-a@chain-a',
                'change_type': 'add_liquidity',
                'liquidity_delta': '5',
                'event_time_ms': 1100,
            },
            {
                'pool_id': 8,
                'pool_application': 'chain-b:pool-app-2',
                'token_0': 'CCC',
                'token_1': 'TLINERA',
                'owner': 'owner-a@chain-a',
                'change_type': 'remove_liquidity',
                'liquidity_delta': '5',
                'event_time_ms': 2100,
            },
        ]
        repository = SettledLiquidityProjectionRepository(db)

        active = repository.get_positions(owner='chain-a:owner-a', status='active')
        closed = repository.get_positions(owner='chain-a:owner-a', status='closed')
        all_rows = repository.get_positions(owner='chain-a:owner-a', status='all')

        self.assertEqual(active, [{
            'pool_application': 'chain-a:pool-app',
            'pool_id': 7,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'owner': 'chain-a:owner-a',
            'status': 'active',
            'current_liquidity': '6',
            'added_liquidity': '10',
            'removed_liquidity': '4',
            'add_tx_count': 1,
            'remove_tx_count': 1,
            'opened_at': 1000,
            'updated_at': 2000,
            'closed_at': None,
        }])
        self.assertEqual(closed, [{
            'pool_application': 'chain-b:pool-app-2',
            'pool_id': 8,
            'token_0': 'CCC',
            'token_1': 'TLINERA',
            'owner': 'chain-a:owner-a',
            'status': 'closed',
            'current_liquidity': '0',
            'added_liquidity': '5',
            'removed_liquidity': '5',
            'add_tx_count': 1,
            'remove_tx_count': 1,
            'opened_at': 1100,
            'updated_at': 2100,
            'closed_at': 2100,
        }])
        self.assertEqual([row['pool_id'] for row in all_rows], [8, 7])

    def test_settled_liquidity_projection_keeps_empty_positions_without_legacy_fallback(self):
        db = self.FakeDb()
        repository = SettledLiquidityProjectionRepository(db)

        rows = repository.get_positions(
            owner='chain-a:owner-a',
            status='active',
        )

        self.assertEqual(rows, [])
        self.assertEqual(db.calls, ['ensure_fresh_read_connection'])

    def test_pool_transaction_history_projection_combines_trade_and_liquidity_history(self):
        class FakeTradeProjectionRepository:
            def get_pool_trade_history(self, **_kwargs):
                return [
                    {
                        'transaction_id': 11,
                        'transaction_type': 'BuyToken0',
                        'created_at': 2000,
                    },
                    {
                        'transaction_id': 12,
                        'transaction_type': 'SellToken0',
                        'created_at': 3000,
                    },
                ]

            def get_transactions(self, **_kwargs):
                return None

            def get_transactions_information(self, **_kwargs):
                return None

            def get_candles(self, **_kwargs):
                return None

            def get_candles_information(self, **_kwargs):
                return None

        class FakeLiquidityProjectionRepository:
            def get_pool_liquidity_history(self, **_kwargs):
                return [
                    {
                        'transaction_id': 10,
                        'transaction_type': 'AddLiquidity',
                        'created_at': 1000,
                    }
                ]

        repository = SettledPoolHistoryProjectionRepository(
            settled_trade_projection_repo=FakeTradeProjectionRepository(),
            settled_liquidity_projection_repo=FakeLiquidityProjectionRepository(),
        )
        pool_history = repository.get_pool_transaction_history(
            pool_application='chain-a:pool-app',
            pool_id=7,
        )
        swap_count = repository.get_pool_swap_count_since(
            pool_application='chain-a:pool-app',
            pool_id=7,
            created_at=1500,
        )
        gap_summary = repository.get_pool_transaction_gap_summary(
            pool_application='chain-a:pool-app',
            pool_id=7,
        )

        self.assertEqual([row['transaction_id'] for row in pool_history], [10, 11, 12])
        self.assertEqual(swap_count, 2)
        self.assertEqual(gap_summary['start_id'], 10)
        self.assertEqual(gap_summary['end_id'], 12)

    def test_get_position_liquidity_history_maps_token_amount_fields_from_projection_rows(self):
        db = self.FakeDb()
        db.cursor_dict.rows = [
            {
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'owner': 'owner-a@chain-a',
                'transaction_id': 13,
                'change_type': 'add_liquidity',
                'liquidity_delta': '5',
                'amount_0_delta': '11',
                'amount_1_delta': '22',
                'event_time_ms': 1234,
            },
            {
                'pool_id': 7,
                'pool_application': 'chain-a:pool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'owner': 'owner-a@chain-a',
                'transaction_id': 14,
                'change_type': 'remove_liquidity',
                'liquidity_delta': '2',
                'amount_0_delta': '3',
                'amount_1_delta': '4',
                'event_time_ms': 2234,
            },
        ]
        repository = SettledLiquidityProjectionRepository(db)

        history = repository.get_position_liquidity_history(
            owner='chain-a:owner-a',
            pool_application='chain-a:pool-app',
            pool_id=None,
        )

        self.assertEqual(
            history,
            [
                {
                    'transaction_id': 13,
                    'transaction_type': 'AddLiquidity',
                    'amount_0_in': '11',
                    'amount_0_out': None,
                    'amount_1_in': '22',
                    'amount_1_out': None,
                    'liquidity': '5',
                    'created_at': 1234,
                    'from_account': 'chain-a:owner-a',
                },
                {
                    'transaction_id': 14,
                    'transaction_type': 'RemoveLiquidity',
                    'amount_0_in': None,
                    'amount_0_out': '3',
                    'amount_1_in': None,
                    'amount_1_out': '4',
                    'liquidity': '2',
                    'created_at': 2234,
                    'from_account': 'chain-a:owner-a',
                },
            ],
        )
