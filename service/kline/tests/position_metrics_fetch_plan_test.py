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


class PositionMetricsFetchPlanTest(unittest.TestCase):
    def test_snapshot_fast_path_plan_owns_stage_and_reason(self):
        plan = PositionMetricsFetchPlan.snapshot_fast_path({'projected_metrics': {'metrics_status': 'exact'}})

        self.assertTrue(plan.is_snapshot_fast_path())
        self.assertEqual(plan.resolved_fetch_stage(), PositionMetricsFetchStage.SNAPSHOT_FAST_PATH)
        self.assertEqual(plan.resolved_fetch_reason_code(), PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_HIT)
        self.assertEqual(plan.resolved_projected_metrics(), {'metrics_status': 'exact'})


if __name__ == '__main__':
    unittest.main()
