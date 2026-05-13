from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot


class PositionMetricsSnapshotInputs:
    def __init__(self, payload: dict | None):
        self.payload = payload or {}
        self._position_basis_snapshot = PositionMetricsPositionBasisSnapshot(
            self.payload.get('position_basis_snapshot')
        )
        self._pool_state_snapshot = PositionMetricsPoolStateSnapshot(
            self.payload.get('pool_state_snapshot')
        )

    def position_basis_snapshot(self):
        return self._position_basis_snapshot

    def pool_state_snapshot(self):
        return self._pool_state_snapshot

    def fast_path_kwargs(
        self,
        *,
        position: dict,
        payload: dict,
    ) -> dict:
        return {
            'position': position,
            'payload': payload,
            'position_basis_snapshot': self.position_basis_snapshot(),
            'pool_state_snapshot': self.pool_state_snapshot(),
        }

    def enrich_kwargs(self, *, replay_bundle) -> dict:
        return {
            'replay_bundle': replay_bundle,
            'position_basis_snapshot': self.position_basis_snapshot(),
            'pool_state_snapshot': self.pool_state_snapshot(),
        }

    def shadow_kwargs(
        self,
        *,
        position: dict,
        projected_metrics: dict,
        replay_summary,
    ) -> dict:
        return {
            'position': position,
            'projected_metrics': projected_metrics,
            'replay_summary': replay_summary,
            'position_basis_snapshot': self.position_basis_snapshot(),
            'pool_state_snapshot': self.pool_state_snapshot(),
        }
