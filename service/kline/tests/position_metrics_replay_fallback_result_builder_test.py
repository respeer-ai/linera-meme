import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_replay_fallback_result_builder import PositionMetricsReplayFallbackResultBuilder  # noqa: E402
from query.read_models.position_metrics_fetch_plan import PositionMetricsFetchPlan  # noqa: E402
from position_metrics_payload_decision import PositionMetricsPayloadDecision  # noqa: E402
from position_metrics_payload_result import PositionMetricsPayloadResult  # noqa: E402


class PositionMetricsReplayFallbackResultBuilderTest(unittest.TestCase):
    def _plan(self):
        return PositionMetricsFetchPlan.replay_fallback(
            PositionMetricsPayloadResult(
                metrics={'metrics_status': 'exact'},
                decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                reason_code='payload_requires_history',
            )
        )

    def test_returns_projected_metrics_only_when_snapshot_shadow_is_absent(self):
        builder = PositionMetricsReplayFallbackResultBuilder()

        result = builder.build(
            projected_metrics={'metrics_status': 'exact'},
            snapshot_shadow=None,
            plan=self._plan(),
        )
        self.assertEqual(result.projected_metrics, {'metrics_status': 'exact'})
        self.assertIsNone(result.snapshot_shadow)

    def test_returns_projected_metrics_and_snapshot_shadow_when_present(self):
        builder = PositionMetricsReplayFallbackResultBuilder()

        result = builder.build(
            projected_metrics={'metrics_status': 'exact'},
            snapshot_shadow={'snapshot_shadow': {'readiness': 'candidate'}},
            plan=self._plan(),
        )
        self.assertEqual(result.projected_metrics, {'metrics_status': 'exact'})
        self.assertEqual(result.snapshot_shadow, {'snapshot_shadow': {'readiness': 'candidate'}})


if __name__ == '__main__':
    unittest.main()
