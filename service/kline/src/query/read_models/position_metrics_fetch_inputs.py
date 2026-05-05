from query.read_models.position_metrics_replay_bundle import PositionMetricsReplayBundle
from query.read_models.position_metrics_replay_summary import PositionMetricsReplaySummary
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs


class PositionMetricsFetchInputs:
    def __init__(
        self,
        *,
        position: dict,
        payload: dict,
        snapshot_inputs,
        replay_bundle_loader,
    ):
        self.position = position
        self.payload = payload
        self._snapshot_inputs = snapshot_inputs
        self._replay_bundle_loader = replay_bundle_loader
        self._replay_bundle = None

    def snapshot_inputs(self) -> PositionMetricsSnapshotInputs:
        return self._snapshot_inputs

    def replay_bundle(self) -> PositionMetricsReplayBundle:
        if self._replay_bundle is None:
            self._replay_bundle = self._replay_bundle_loader()
        return self._replay_bundle

    def fast_path_kwargs(self) -> dict:
        return self.snapshot_inputs().fast_path_kwargs(
            position=self.position,
            payload=self.payload,
        )

    def enrich_kwargs(self) -> dict:
        return self.snapshot_inputs().enrich_kwargs(
            replay_bundle=self.replay_bundle(),
        )

    def replay_summary(self):
        replay_summary = self.replay_bundle().replay_summary()
        if isinstance(replay_summary, PositionMetricsReplaySummary):
            return replay_summary
        return PositionMetricsReplaySummary(replay_summary)
