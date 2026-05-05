from query.read_models.position_metrics_replay_bundle import PositionMetricsReplayBundle
from query.read_models.position_metrics_replay_facts import PositionMetricsReplayFacts
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs
from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError


class PositionMetricsProductStateQueryInputProvider:
    def __init__(
        self,
        *,
        snapshot_inputs_repository,
        replay_facts_repository,
    ):
        self.snapshot_inputs_repository = snapshot_inputs_repository
        self.replay_facts_repository = replay_facts_repository

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

    def load_replay_bundle(
        self,
        *,
        position: dict,
    ) -> PositionMetricsReplayBundle:
        if self.replay_facts_repository is None:
            raise ProjectionQueryUnavailableError('position_metrics_replay_facts')
        payload = self.replay_facts_repository.get_replay_facts(
            owner=position['owner'],
            pool_application=position['pool_application'],
            pool_id=position['pool_id'],
            opened_at=int(position['opened_at']) if position.get('opened_at') is not None else None,
        )
        if isinstance(payload, PositionMetricsReplayBundle):
            return payload
        if not isinstance(payload, PositionMetricsReplayFacts):
            payload = PositionMetricsReplayFacts(payload)
        return PositionMetricsReplayBundle(payload)
