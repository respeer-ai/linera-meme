import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.settled_pool_history_projection_repo import SettledPoolHistoryProjectionRepository  # noqa: E402
from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError  # noqa: E402


class SettledPoolHistoryProjectionRepositoryTest(unittest.TestCase):
    def test_combines_trade_and_liquidity_history_when_projection_is_available(self):
        class FakeTradeProjectionRepository:
            def get_pool_trade_history(self, **_kwargs):
                return [
                    {'transaction_id': 11, 'created_at': 2000, 'transaction_type': 'BuyToken0'},
                    {'transaction_id': 13, 'created_at': 4000, 'transaction_type': 'SellToken0'},
                ]

        class FakeLiquidityProjectionRepository:
            def get_pool_liquidity_history(self, **_kwargs):
                return [
                    {'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
                    {'transaction_id': 12, 'created_at': 3000, 'transaction_type': 'RemoveLiquidity'},
                ]

        repository = SettledPoolHistoryProjectionRepository(
            settled_trade_projection_repo=FakeTradeProjectionRepository(),
            settled_liquidity_projection_repo=FakeLiquidityProjectionRepository(),
        )

        history = repository.get_pool_transaction_history(
            pool_application='chain:pool-app',
            pool_id=7,
        )
        swap_count = repository.get_pool_swap_count_since(
            pool_application='chain:pool-app',
            pool_id=7,
            created_at=2500,
        )
        gap_summary = repository.get_pool_transaction_gap_summary(
            pool_application='chain:pool-app',
            pool_id=7,
        )

        self.assertEqual([row['transaction_id'] for row in history], [10, 11, 12, 13])
        self.assertEqual(swap_count, 1)
        self.assertEqual(
            gap_summary,
            {
                'has_internal_gaps': False,
                'start_id': 10,
                'end_id': 13,
                'missing_count': 0,
                'missing_ids_sample': [],
                'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
            },
        )

    def test_raises_when_projection_is_unavailable(self):
        class MissingTradeProjectionRepository:
            def get_pool_trade_history(self, **_kwargs):
                return None

        class MissingLiquidityProjectionRepository:
            def get_pool_liquidity_history(self, **_kwargs):
                return None

        repository = SettledPoolHistoryProjectionRepository(
            settled_trade_projection_repo=MissingTradeProjectionRepository(),
            settled_liquidity_projection_repo=MissingLiquidityProjectionRepository(),
        )

        with self.assertRaises(ProjectionQueryUnavailableError):
            repository.get_pool_transaction_history(
                pool_application='chain:pool-app',
                pool_id=7,
            )
