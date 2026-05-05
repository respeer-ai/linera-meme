import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_replay_fallback_result_builder import PositionMetricsReplayFallbackResultBuilder  # noqa: E402


class PositionMetricsReplayFallbackResultBuilderTest(unittest.TestCase):
    def test_returns_live_metrics_only_when_snapshot_shadow_is_absent(self):
        builder = PositionMetricsReplayFallbackResultBuilder()

        self.assertEqual(
            builder.build(
                live_metrics={'metrics_status': 'exact'},
                snapshot_shadow=None,
            ),
            {'live_metrics': {'metrics_status': 'exact'}},
        )

    def test_returns_live_metrics_and_snapshot_shadow_when_present(self):
        builder = PositionMetricsReplayFallbackResultBuilder()

        self.assertEqual(
            builder.build(
                live_metrics={'metrics_status': 'exact'},
                snapshot_shadow={'snapshot_shadow': {'readiness': 'candidate'}},
            ),
            {
                'live_metrics': {'metrics_status': 'exact'},
                'snapshot_shadow': {'snapshot_shadow': {'readiness': 'candidate'}},
            },
        )


if __name__ == '__main__':
    unittest.main()
