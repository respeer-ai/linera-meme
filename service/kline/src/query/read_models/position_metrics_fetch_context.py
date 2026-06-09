from query.read_models.position_metrics_fetch_inputs import PositionMetricsFetchInputs


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
            )
        return self._fetch_inputs
