import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_fast_path_executor import PositionMetricsFastPathExecutor  # noqa: E402
from query.read_models.position_metrics_fetch_plan import PositionMetricsFetchPlan  # noqa: E402
from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult  # noqa: E402


class PositionMetricsFastPathExecutorTest(unittest.TestCase):
    def test_wraps_fast_path_payload_with_plan_metadata(self):
        executor = PositionMetricsFastPathExecutor()
        plan = PositionMetricsFetchPlan.snapshot_fast_path(
            {'projected_metrics': {'metrics_status': 'exact'}}
        )

        result = executor.execute(plan=plan)
        self.assertIsInstance(result, PositionMetricsFetchedResult)
        self.assertEqual(result.projected_metrics, {'metrics_status': 'exact'})
        self.assertEqual(result.fetch_stage, 'snapshot_fast_path')
        self.assertEqual(result.fetch_reason_code, 'snapshot_fast_path_hit')
        self.assertIsNone(result.snapshot_shadow)


if __name__ == '__main__':
    unittest.main()
