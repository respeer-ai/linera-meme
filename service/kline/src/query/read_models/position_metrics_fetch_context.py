from query.read_models.position_metrics_fetch_inputs import PositionMetricsFetchInputs
from query.read_models.position_metrics_replay_bundle import PositionMetricsReplayBundle


class PositionMetricsFetchContext:
    def __init__(
        self,
        *,
        position: dict,
        payload: dict,
        query_input_provider,
        snapshot_inputs=None,
    ):
        self.position = position
        self.payload = payload
        self.query_input_provider = query_input_provider
        self._snapshot_inputs = snapshot_inputs
        self._fetch_inputs = None

    def fetch_inputs(self):
        if self._fetch_inputs is None:
            snapshot_inputs = self._snapshot_inputs
            if snapshot_inputs is None:
                snapshot_inputs = self.query_input_provider.load_snapshot_inputs(
                    position=self.position,
                )
            self._fetch_inputs = PositionMetricsFetchInputs(
                position=self.position,
                payload=self.payload,
                snapshot_inputs=snapshot_inputs,
                replay_bundle_loader=self._load_replay_bundle,
            )
        return self._fetch_inputs

    def _load_replay_bundle(self):
        return self.query_input_provider.load_replay_bundle(
            position=self.position,
        )
