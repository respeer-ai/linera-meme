import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_fetch_plan import PositionMetricsFetchPlan  # noqa: E402
from query.read_models.position_metrics_payload_only_executor import PositionMetricsPayloadOnlyExecutor  # noqa: E402
from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult  # noqa: E402
from position_metrics_payload_decision import PositionMetricsPayloadDecision  # noqa: E402
from position_metrics_payload_result import PositionMetricsPayloadResult  # noqa: E402


class PositionMetricsPayloadOnlyExecutorTest(unittest.TestCase):
    def test_wraps_payload_only_metrics_with_plan_metadata(self):
        executor = PositionMetricsPayloadOnlyExecutor()
        plan = PositionMetricsFetchPlan.payload_only(
            PositionMetricsPayloadResult(
                metrics={'metrics_status': 'partial_projected_redeemable_only'},
                decision=PositionMetricsPayloadDecision.PAYLOAD_ONLY,
                reason_code='payload_history_unavailable',
            )
        )

        result = executor.execute(plan=plan)
        self.assertIsInstance(result, PositionMetricsFetchedResult)
        self.assertEqual(result.projected_metrics, {'metrics_status': 'partial_projected_redeemable_only'})
        self.assertEqual(result.fetch_stage, 'payload_only')
        self.assertEqual(result.fetch_reason_code, 'snapshot_fast_path_miss_payload_only')


if __name__ == '__main__':
    unittest.main()
