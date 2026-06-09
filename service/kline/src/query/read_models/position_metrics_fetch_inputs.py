from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs


class PositionMetricsFetchInputs:
    def __init__(
        self,
        *,
        position: dict,
        payload: dict,
        snapshot_inputs,
    ):
        self.position = position
        self.payload = payload
        self._snapshot_inputs = snapshot_inputs

    def snapshot_inputs(self) -> PositionMetricsSnapshotInputs:
        return self._snapshot_inputs

    def fast_path_kwargs(self) -> dict:
        return self.snapshot_inputs().fast_path_kwargs(
            position=self.position,
            payload=self.payload,
        )
