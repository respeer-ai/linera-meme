class PositionMetricsSnapshotProjectionRepository:
    def __init__(
        self,
        *,
        position_state_projection_repo,
        pool_state_projection_repo,
    ):
        self.position_state_projection_repo = position_state_projection_repo
        self.pool_state_projection_repo = pool_state_projection_repo

    def get_snapshot_inputs(
        self,
        *,
        owner: str,
        pool_application_id: str,
        status: str = 'active',
    ) -> dict | None:
        position_basis_snapshot = self.position_state_projection_repo.get_position_basis_snapshot(
            owner=owner,
            pool_application_id=pool_application_id,
            status=status,
        )
        pool_state_snapshot = self.pool_state_projection_repo.get_pool_state_snapshot(
            pool_application_id=pool_application_id,
        )
        if position_basis_snapshot is None and pool_state_snapshot is None:
            return None
        return {
            'position_basis_snapshot': position_basis_snapshot,
            'pool_state_snapshot': pool_state_snapshot,
        }
