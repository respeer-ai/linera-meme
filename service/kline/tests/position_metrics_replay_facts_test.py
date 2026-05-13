import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_replay_facts import PositionMetricsReplayFacts  # noqa: E402


class PositionMetricsReplayFactsTest(unittest.TestCase):
    def test_exposes_replay_fact_fields_through_named_accessors(self):
        facts = PositionMetricsReplayFacts(
            {
                'liquidity_history': [{'transaction_id': 10}],
                'pool_transaction_history': [{'transaction_id': 11}],
                'pool_swap_count_since_open': 3,
                'pool_history_gap_summary': {'has_internal_gaps': False},
                'replay_summary': {'latest_pool_transaction_id': 11},
            }
        )

        self.assertEqual(facts.liquidity_history(), [{'transaction_id': 10}])
        self.assertEqual(facts.pool_transaction_history(), [{'transaction_id': 11}])
        self.assertEqual(facts.pool_swap_count_since_open(), 3)
        self.assertEqual(facts.pool_history_gap_summary(), {'has_internal_gaps': False})
        self.assertEqual(facts.replay_summary().as_dict(), {'latest_pool_transaction_id': 11})
