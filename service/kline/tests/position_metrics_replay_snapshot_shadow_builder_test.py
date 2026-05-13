import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_replay_snapshot_shadow_builder import PositionMetricsReplaySnapshotShadowBuilder  # noqa: E402
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402


class PositionMetricsReplaySnapshotShadowBuilderTest(unittest.TestCase):
    def test_returns_none_when_shadow_evaluator_is_disabled(self):
        builder = PositionMetricsReplaySnapshotShadowBuilder()

        self.assertIsNone(
            builder.build(
                snapshot_inputs=PositionMetricsSnapshotInputs({}),
                position={'owner': 'chain:owner-a'},
                projected_metrics={'metrics_status': 'exact'},
                replay_summary=None,
            )
        )

    def test_returns_shadow_payload_when_evaluator_is_enabled(self):
        class FakeEvaluator:
            def evaluate(self, **kwargs):
                self.kwargs = dict(kwargs)
                return {'snapshot_shadow': {'readiness': 'candidate'}}

        builder = PositionMetricsReplaySnapshotShadowBuilder(
            snapshot_shadow_evaluator=FakeEvaluator(),
        )

        self.assertEqual(
            builder.build(
                snapshot_inputs=PositionMetricsSnapshotInputs(
                    {
                        'position_basis_snapshot': {'basis_transaction_id': 11},
                        'pool_state_snapshot': {'last_transaction_id': 12},
                    }
                ),
                position={'owner': 'chain:owner-a'},
                projected_metrics={'metrics_status': 'exact'},
                replay_summary={
                    'latest_position_transaction_id': 11,
                    'latest_pool_transaction_id': 12,
                },
            ),
            {'snapshot_shadow': {'readiness': 'candidate'}},
        )


if __name__ == '__main__':
    unittest.main()
