import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.position_metrics_snapshot_materializer import PositionMetricsSnapshotMaterializer  # noqa: E402
from market.settled_output_batch_factory import SettledOutputBatchFactory  # noqa: E402


class PositionMetricsSnapshotMaterializerTest(unittest.TestCase):
    class FakeSnapshotBuilder:
        def __init__(self, *, should_fail=False):
            self.should_fail = should_fail
            self.calls = []

        def build_materialization_plan(self, output_batch):
            self.calls.append(output_batch)
            if self.should_fail:
                raise RuntimeError('snapshot rebuild failed')
            return {
                'pool_states': [{'pool_state_id': 'pool-1'}],
                'position_replacements': [
                    {
                        'owner': 'chain-user:owner-a',
                        'pool_application_id': 'chain-a:pool-app',
                        'states': [{'position_state_id': 'pos-1'}],
                    }
                ],
                'affected_pool_count': 1,
                'affected_position_count': 1,
            }

    class FakePositionStateSnapshotRepository:
        def __init__(self):
            self.calls = []

        def replace_position_states(self, **kwargs):
            self.calls.append(dict(kwargs))
            return len(kwargs['states'])

    class FakePoolStateSnapshotRepository:
        def __init__(self):
            self.calls = []

        def upsert_pool_states(self, states):
            self.calls.append(list(states))
            return len(states)

    def test_materialize_outputs_persists_replacements_and_pool_states(self):
        position_repository = self.FakePositionStateSnapshotRepository()
        pool_repository = self.FakePoolStateSnapshotRepository()
        materializer = PositionMetricsSnapshotMaterializer(
            snapshot_builder=self.FakeSnapshotBuilder(),
            position_state_snapshot_repository=position_repository,
            pool_state_snapshot_repository=pool_repository,
        )
        output_batch = SettledOutputBatchFactory().build(
            [{'settled_output_type': 'settled_trade', 'pool_application_id': 'chain-a:pool-app'}]
        )

        summary = materializer.materialize_output_batch(output_batch)

        self.assertFalse(summary['degraded'])
        self.assertEqual(summary['persisted_pool_state_count'], 1)
        self.assertEqual(summary['persisted_position_state_count'], 1)
        self.assertEqual(len(position_repository.calls), 1)
        self.assertEqual(len(pool_repository.calls), 1)
        self.assertEqual(len(materializer.snapshot_builder.calls), 1)
        self.assertEqual(
            materializer.snapshot_builder.calls[0].trades(),
            [{'settled_output_type': 'settled_trade', 'pool_application_id': 'chain-a:pool-app'}],
        )

    def test_materialize_outputs_is_fail_open_when_snapshot_rebuild_raises(self):
        position_repository = self.FakePositionStateSnapshotRepository()
        pool_repository = self.FakePoolStateSnapshotRepository()
        materializer = PositionMetricsSnapshotMaterializer(
            snapshot_builder=self.FakeSnapshotBuilder(should_fail=True),
            position_state_snapshot_repository=position_repository,
            pool_state_snapshot_repository=pool_repository,
        )
        output_batch = SettledOutputBatchFactory().build(
            [{'settled_output_type': 'settled_trade', 'pool_application_id': 'chain-a:pool-app'}]
        )

        summary = materializer.materialize_output_batch(output_batch)

        self.assertTrue(summary['degraded'])
        self.assertEqual(summary['error_text'], 'snapshot rebuild failed')
        self.assertEqual(position_repository.calls, [])
        self.assertEqual(pool_repository.calls, [])
        self.assertEqual(len(materializer.snapshot_builder.calls), 1)


if __name__ == '__main__':
    unittest.main()
