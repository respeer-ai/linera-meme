from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs
from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError


class PositionMetricsProductStateQueryInputProvider:
    def __init__(
        self,
        *,
        snapshot_inputs_repository,
    ):
        self.snapshot_inputs_repository = snapshot_inputs_repository

    def load_snapshot_inputs(
        self,
        *,
        position: dict,
    ) -> PositionMetricsSnapshotInputs:
        if self.snapshot_inputs_repository is None:
            raise ProjectionQueryUnavailableError('position_metrics_snapshot_inputs')
        payload = self.snapshot_inputs_repository.get_snapshot_inputs(
            owner=position['owner'],
            pool_application_id=position['pool_application'],
            status=position.get('status') or 'active',
        )
        if isinstance(payload, PositionMetricsSnapshotInputs):
            return payload
        return PositionMetricsSnapshotInputs(payload)
