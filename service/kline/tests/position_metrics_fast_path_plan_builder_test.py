import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_fast_path_plan_builder import PositionMetricsFastPathPlanBuilder  # noqa: E402


class PositionMetricsFastPathPlanBuilderTest(unittest.TestCase):
    def test_returns_none_when_fast_path_is_unconfigured(self):
        self.assertIsNone(
            PositionMetricsFastPathPlanBuilder().build(fetch_context=object())
        )

    def test_returns_snapshot_fast_path_plan_when_fast_path_hits(self):
        class FakeFastPath:
            def resolve(self, **kwargs):
                self.kwargs = dict(kwargs)
                return {'live_metrics': {'metrics_status': 'exact'}}

        class FakeFetchContext:
            class FakeFetchInputs:
                def fast_path_kwargs(self):
                    return {'payload': {'data': {}}}

            def fetch_inputs(self):
                return self.FakeFetchInputs()

        plan = PositionMetricsFastPathPlanBuilder(
            snapshot_fast_path=FakeFastPath(),
        ).build(fetch_context=FakeFetchContext())

        self.assertTrue(plan.is_snapshot_fast_path())
        self.assertEqual(plan.resolved_fetch_reason_code(), 'snapshot_fast_path_hit')


if __name__ == '__main__':
    unittest.main()
