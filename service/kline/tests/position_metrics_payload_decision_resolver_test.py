import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_payload_decision_resolver import PositionMetricsPayloadDecisionResolver  # noqa: E402
from position_metrics_payload_decision import PositionMetricsPayloadDecision  # noqa: E402


class PositionMetricsPayloadDecisionResolverTest(unittest.TestCase):
    def test_returns_payload_only_when_no_history_inputs_are_available(self):
        partial_metrics = {'metrics_status': 'partial_live_redeemable_only'}
        result = PositionMetricsPayloadDecisionResolver().resolve(
            partial_metrics,
            liquidity_history=None,
            pool_transaction_history=None,
            pool_swap_count_since_open=None,
        )

        self.assertEqual(result.decision, PositionMetricsPayloadDecision.PAYLOAD_ONLY)
        self.assertEqual(result.reason_code, 'payload_history_unavailable')
        self.assertEqual(result.metrics, partial_metrics)

    def test_returns_history_enrichment_when_any_history_input_exists(self):
        partial_metrics = {'metrics_status': 'partial_live_redeemable_only'}
        result = PositionMetricsPayloadDecisionResolver().resolve(
            partial_metrics,
            liquidity_history=[],
            pool_transaction_history=[],
            pool_swap_count_since_open=0,
        )

        self.assertEqual(result.decision, PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT)
        self.assertEqual(result.reason_code, 'payload_requires_history')
        self.assertEqual(result.metrics, partial_metrics)
