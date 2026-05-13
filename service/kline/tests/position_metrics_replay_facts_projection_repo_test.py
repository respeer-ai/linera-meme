import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.position_metrics_replay_facts_projection_repo import PositionMetricsReplayFactsProjectionRepository  # noqa: E402


class PositionMetricsReplayFactsProjectionRepositoryTest(unittest.TestCase):
    def test_builds_bundled_replay_facts_from_projection_contracts(self):
        class FakeSettledLiquidityProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_position_liquidity_history(self, **kwargs):
                self.calls.append(('get_position_liquidity_history', dict(kwargs)))
                return [{'transaction_id': 10, 'transaction_type': 'AddLiquidity'}]

        class FakeSettledPoolHistoryProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_pool_transaction_history(self, **kwargs):
                self.calls.append(('get_pool_transaction_history', dict(kwargs)))
                return [{'transaction_id': 11, 'transaction_type': 'BuyToken0'}]

            def get_pool_swap_count_since(self, **kwargs):
                self.calls.append(('get_pool_swap_count_since', dict(kwargs)))
                return 3

            def get_pool_transaction_gap_summary(self, **kwargs):
                self.calls.append(('get_pool_transaction_gap_summary', dict(kwargs)))
                return {'has_internal_gaps': False}

        liquidity_repo = FakeSettledLiquidityProjectionRepository()
        history_repo = FakeSettledPoolHistoryProjectionRepository()
        repository = PositionMetricsReplayFactsProjectionRepository(
            settled_liquidity_projection_repo=liquidity_repo,
            settled_pool_history_projection_repo=history_repo,
        )

        payload = repository.get_replay_facts(
            owner='chain:owner-a',
            pool_application='chain:pool-app',
            pool_id=5,
            opened_at=1200,
        )

        self.assertEqual(
            payload.liquidity_history(),
            [{'transaction_id': 10, 'transaction_type': 'AddLiquidity'}],
        )
        self.assertEqual(
            payload.pool_transaction_history(),
            [{'transaction_id': 11, 'transaction_type': 'BuyToken0'}],
        )
        self.assertEqual(payload.pool_swap_count_since_open(), 3)
        self.assertEqual(payload.pool_history_gap_summary(), {'has_internal_gaps': False})
        self.assertEqual(
            payload.replay_summary().as_dict(),
            {
                'latest_position_transaction_id': 10,
                'latest_position_created_at': None,
                'latest_pool_transaction_id': 11,
                'latest_pool_trade_time_ms': None,
                'latest_pool_liquidity_event_time_ms': None,
            },
        )
        self.assertEqual(
            liquidity_repo.calls,
            [
                (
                    'get_position_liquidity_history',
                    {'owner': 'chain:owner-a', 'pool_application': 'chain:pool-app', 'pool_id': 5},
                )
            ],
        )
        self.assertEqual(
            history_repo.calls,
            [
                ('get_pool_transaction_history', {'pool_application': 'chain:pool-app', 'pool_id': 5}),
                (
                    'get_pool_swap_count_since',
                    {'pool_application': 'chain:pool-app', 'pool_id': 5, 'created_at': 1200},
                ),
                ('get_pool_transaction_gap_summary', {'pool_application': 'chain:pool-app', 'pool_id': 5}),
            ],
        )
