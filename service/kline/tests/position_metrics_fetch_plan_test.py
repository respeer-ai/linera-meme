import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_fetch_plan import PositionMetricsFetchPlan  # noqa: E402
from query.read_models.position_metrics_fetch_reason_code import PositionMetricsFetchReasonCode  # noqa: E402
from query.read_models.position_metrics_fetch_stage import PositionMetricsFetchStage  # noqa: E402
from position_metrics_payload_decision import PositionMetricsPayloadDecision  # noqa: E402
from position_metrics_payload_result import PositionMetricsPayloadResult  # noqa: E402


class PositionMetricsFetchPlanTest(unittest.TestCase):
    def test_snapshot_fast_path_plan_owns_stage_and_reason(self):
        plan = PositionMetricsFetchPlan.snapshot_fast_path({'live_metrics': {'metrics_status': 'exact'}})

        self.assertTrue(plan.is_snapshot_fast_path())
        self.assertFalse(plan.is_payload_only())
        self.assertFalse(plan.needs_replay_fallback())
        self.assertEqual(plan.resolved_fetch_stage(), PositionMetricsFetchStage.SNAPSHOT_FAST_PATH)
        self.assertEqual(plan.resolved_fetch_reason_code(), PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_HIT)
        self.assertEqual(plan.resolved_live_metrics(), {'metrics_status': 'exact'})

    def test_payload_only_plan_owns_stage_and_reason(self):
        payload_result = PositionMetricsPayloadResult(
            metrics={'metrics_status': 'partial_live_redeemable_only'},
            decision=PositionMetricsPayloadDecision.PAYLOAD_ONLY,
            reason_code='payload_history_unavailable',
        )

        plan = PositionMetricsFetchPlan.payload_only(payload_result)

        self.assertFalse(plan.is_snapshot_fast_path())
        self.assertTrue(plan.is_payload_only())
        self.assertFalse(plan.needs_replay_fallback())
        self.assertEqual(plan.resolved_fetch_stage(), PositionMetricsFetchStage.PAYLOAD_ONLY)
        self.assertEqual(
            plan.resolved_fetch_reason_code(),
            PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_PAYLOAD_ONLY,
        )
        self.assertEqual(plan.resolved_live_metrics(), {'metrics_status': 'partial_live_redeemable_only'})

    def test_replay_fallback_plan_owns_stage_and_reason(self):
        payload_result = PositionMetricsPayloadResult(
            metrics={'metrics_status': 'exact'},
            decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
            reason_code='payload_requires_history',
        )

        plan = PositionMetricsFetchPlan.replay_fallback(payload_result)

        self.assertFalse(plan.is_snapshot_fast_path())
        self.assertFalse(plan.is_payload_only())
        self.assertTrue(plan.needs_replay_fallback())
        self.assertEqual(plan.resolved_fetch_stage(), PositionMetricsFetchStage.REPLAY_FALLBACK)
        self.assertEqual(
            plan.resolved_fetch_reason_code(),
            PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_PAYLOAD_REQUIRES_HISTORY,
        )
        self.assertEqual(plan.resolved_live_metrics(), {'metrics_status': 'exact'})


if __name__ == '__main__':
    unittest.main()
