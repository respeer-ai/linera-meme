import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_replay_summary import PositionMetricsReplaySummary  # noqa: E402


class PositionMetricsReplaySummaryTest(unittest.TestCase):
    def test_exposes_replay_summary_fields_through_named_accessors(self):
        summary = PositionMetricsReplaySummary(
            {
                'latest_position_transaction_id': 10,
                'latest_position_created_at': 1000,
                'latest_pool_transaction_id': 11,
                'latest_pool_trade_time_ms': 1100,
                'latest_pool_liquidity_event_time_ms': 1050,
            }
        )

        self.assertEqual(summary.latest_position_transaction_id(), 10)
        self.assertEqual(summary.latest_position_created_at(), 1000)
        self.assertEqual(summary.latest_pool_transaction_id(), 11)
        self.assertEqual(summary.latest_pool_trade_time_ms(), 1100)
        self.assertEqual(summary.latest_pool_liquidity_event_time_ms(), 1050)
        self.assertEqual(
            summary.as_dict(),
            {
                'latest_position_transaction_id': 10,
                'latest_position_created_at': 1000,
                'latest_pool_transaction_id': 11,
                'latest_pool_trade_time_ms': 1100,
                'latest_pool_liquidity_event_time_ms': 1050,
            },
        )
        self.assertEqual(
            summary.shadow_latest_dict(),
            {
                'latest_position_transaction_id': 10,
                'latest_position_created_at': 1000,
                'latest_pool_transaction_id': 11,
                'latest_pool_trade_time_ms': 1100,
                'latest_pool_liquidity_event_time_ms': 1050,
            },
        )

    def test_projects_canonical_summary_from_histories(self):
        summary = PositionMetricsReplaySummary.from_histories(
            liquidity_history=[
                {'transaction_id': '8', 'transaction_type': 'AddLiquidity', 'created_at': 900},
                {'transaction_id': '10', 'transaction_type': 'RemoveLiquidity', 'created_at': 1000},
            ],
            pool_transaction_history=[
                {'transaction_id': '11', 'transaction_type': 'BuyToken0', 'created_at': 1100},
                {'transaction_id': '9', 'transaction_type': 'AddLiquidity', 'created_at': 1050},
                {'transaction_id': '12', 'transaction_type': 'RemoveLiquidity', 'created_at': 1080},
            ],
        )

        self.assertEqual(summary.latest_position_transaction_id(), 10)
        self.assertEqual(summary.latest_position_created_at(), 1000)
        self.assertEqual(summary.latest_pool_transaction_id(), 11)
        self.assertEqual(summary.latest_pool_trade_time_ms(), 1100)
        self.assertEqual(summary.latest_pool_liquidity_event_time_ms(), 1080)
