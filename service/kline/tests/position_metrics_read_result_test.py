import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_read_result import PositionMetricsReadResult  # noqa: E402


class PositionMetricsReadResultTest(unittest.TestCase):
    def test_returns_public_payload_without_shadow_diagnostics(self):
        result = PositionMetricsReadResult(
            owner='chain:owner-a',
            metrics=[{'pool_id': 5}],
            metric_diagnostics=[{'pool_id': 5, 'fetch_stage': 'payload_only'}],
            shadow_diagnostics=[{'pool_id': 5}],
        )

        self.assertEqual(
            result.public_payload(),
            {
                'owner': 'chain:owner-a',
                'metrics': [{'pool_id': 5}],
            },
        )
        self.assertEqual(result.metric_diagnostics, [{'pool_id': 5, 'fetch_stage': 'payload_only'}])
        self.assertEqual(result.shadow_diagnostics, [{'pool_id': 5}])


if __name__ == '__main__':
    unittest.main()
