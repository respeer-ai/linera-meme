from query.read_models.position_metrics_replay_summary import PositionMetricsReplaySummary


class PositionMetricsReplaySnapshotShadowBuilder:
    def __init__(
        self,
        *,
        snapshot_shadow_evaluator=None,
    ):
        self.snapshot_shadow_evaluator = snapshot_shadow_evaluator

    def build(
        self,
        *,
        snapshot_inputs,
        position: dict,
        projected_metrics: dict,
        replay_summary,
    ):
        if self.snapshot_shadow_evaluator is None:
            return None
        if not isinstance(replay_summary, PositionMetricsReplaySummary):
            replay_summary = PositionMetricsReplaySummary(replay_summary)
        return self.snapshot_shadow_evaluator.evaluate(
            **snapshot_inputs.shadow_kwargs(
                position=position,
                projected_metrics=projected_metrics,
                replay_summary=replay_summary,
            )
        )
