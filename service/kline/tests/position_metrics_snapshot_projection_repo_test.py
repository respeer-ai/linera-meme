import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from storage.mysql.position_metrics_snapshot_projection_repo import PositionMetricsSnapshotProjectionRepository  # noqa: E402
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402


class PositionMetricsSnapshotProjectionRepositoryTest(unittest.TestCase):
    def test_get_snapshot_inputs_returns_combined_snapshots(self):
        class FakePositionStateProjectionRepository:
            def get_position_basis_snapshot(self, **kwargs):
                self.kwargs = dict(kwargs)
                return {'position_state_id': 'pos-1'}

        class FakePoolStateProjectionRepository:
            def get_pool_state_snapshot(self, **kwargs):
                self.kwargs = dict(kwargs)
                return {'pool_state_id': 'pool-1'}

        position_repo = FakePositionStateProjectionRepository()
        pool_repo = FakePoolStateProjectionRepository()
        repository = PositionMetricsSnapshotProjectionRepository(
            position_state_projection_repo=position_repo,
            pool_state_projection_repo=pool_repo,
        )

        payload = repository.get_snapshot_inputs(
            owner='chain:owner-a',
            pool_application_id='chain:pool-app',
        )

        self.assertIsInstance(payload, PositionMetricsSnapshotInputs)
        self.assertEqual(payload.position_basis_snapshot().raw(), {'position_state_id': 'pos-1'})
        self.assertEqual(payload.pool_state_snapshot().raw(), {'pool_state_id': 'pool-1'})
        self.assertEqual(
            position_repo.kwargs,
            {
                'owner': 'chain:owner-a',
                'pool_application_id': 'chain:pool-app',
                'status': 'active',
            },
        )
        self.assertEqual(
            pool_repo.kwargs,
            {'pool_application_id': 'chain:pool-app'},
        )

    def test_get_snapshot_inputs_returns_none_when_both_missing(self):
        class FakePositionStateProjectionRepository:
            def get_position_basis_snapshot(self, **_kwargs):
                return None

        class FakePoolStateProjectionRepository:
            def get_pool_state_snapshot(self, **_kwargs):
                return None

        repository = PositionMetricsSnapshotProjectionRepository(
            position_state_projection_repo=FakePositionStateProjectionRepository(),
            pool_state_projection_repo=FakePoolStateProjectionRepository(),
        )

        self.assertIsNone(
            repository.get_snapshot_inputs(
                owner='chain:owner-a',
                pool_application_id='chain:pool-app',
            )
        )

    def test_get_snapshot_inputs_can_return_pool_snapshot_without_owner(self):
        class FakePositionStateProjectionRepository:
            def get_position_basis_snapshot(self, **_kwargs):
                raise AssertionError('owner-less snapshot query should not read position state')

        class FakePoolStateProjectionRepository:
            def get_pool_state_snapshot(self, **kwargs):
                self.kwargs = dict(kwargs)
                return {'pool_state_id': 'pool-1'}

        pool_repo = FakePoolStateProjectionRepository()
        repository = PositionMetricsSnapshotProjectionRepository(
            position_state_projection_repo=FakePositionStateProjectionRepository(),
            pool_state_projection_repo=pool_repo,
        )

        payload = repository.get_snapshot_inputs(
            owner=None,
            pool_application_id='chain:pool-app',
        )
        self.assertIsInstance(payload, PositionMetricsSnapshotInputs)
        self.assertIsNone(payload.position_basis_snapshot().raw())
        self.assertEqual(payload.pool_state_snapshot().raw(), {'pool_state_id': 'pool-1'})
        self.assertEqual(pool_repo.kwargs, {'pool_application_id': 'chain:pool-app'})


if __name__ == '__main__':
    unittest.main()
