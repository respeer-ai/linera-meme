from storage.mysql.pool_state_projection_repo import PoolStateProjectionRepository
from storage.mysql.position_metrics_snapshot_projection_repo import PositionMetricsSnapshotProjectionRepository
from storage.mysql.position_state_projection_repo import PositionStateProjectionRepository
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs


class PositionMetricsSnapshotInputsProjectionRepository:
    def __init__(
        self,
        db,
        *,
        position_state_projection_repo=None,
        pool_state_projection_repo=None,
        snapshot_projection_repo=None,
    ):
        self.db = db
        self.position_state_projection_repo = (
            position_state_projection_repo
            or PositionStateProjectionRepository(db)
        )
        self.pool_state_projection_repo = (
            pool_state_projection_repo
            or PoolStateProjectionRepository(db)
        )
        self.snapshot_projection_repo = (
            snapshot_projection_repo
            or PositionMetricsSnapshotProjectionRepository(
                position_state_projection_repo=self.position_state_projection_repo,
                pool_state_projection_repo=self.pool_state_projection_repo,
            )
        )

    def get_snapshot_inputs(
        self,
        *,
        owner: str | None,
        pool_application_id: str,
        status: str = 'active',
    ) -> PositionMetricsSnapshotInputs | None:
        return self.snapshot_projection_repo.get_snapshot_inputs(
            owner=owner,
            pool_application_id=pool_application_id,
            status=status,
        )
