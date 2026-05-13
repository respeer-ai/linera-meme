import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult  # noqa: E402


class PositionMetricsFetchedResultTest(unittest.TestCase):
    def test_wraps_plain_projected_metrics_payload(self):
        result = PositionMetricsFetchedResult.from_fetcher_payload(
            {'metrics_status': 'partial'}
        )

        self.assertEqual(result.projected_metrics, {'metrics_status': 'partial'})
        self.assertIsNone(result.fetch_stage)
        self.assertIsNone(result.fetch_reason_code)
        self.assertIsNone(result.snapshot_shadow)

    def test_wraps_composite_fetcher_payload(self):
        result = PositionMetricsFetchedResult.from_fetcher_payload(
            {
                'projected_metrics': {'metrics_status': 'exact'},
                'fetch_stage': 'snapshot_fast_path',
                'fetch_reason_code': 'snapshot_fast_path_hit',
                'snapshot_shadow': {'snapshot_shadow': {'readiness': 'candidate'}},
            }
        )

        self.assertEqual(result.projected_metrics, {'metrics_status': 'exact'})
        self.assertEqual(result.fetch_stage, 'snapshot_fast_path')
        self.assertEqual(result.fetch_reason_code, 'snapshot_fast_path_hit')
        self.assertEqual(
            result.snapshot_shadow,
            {'snapshot_shadow': {'readiness': 'candidate'}},
        )


if __name__ == '__main__':
    unittest.main()
