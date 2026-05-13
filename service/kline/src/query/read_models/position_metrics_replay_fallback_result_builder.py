from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult


class PositionMetricsReplayFallbackResultBuilder:
    def build(
        self,
        *,
        projected_metrics: dict,
        snapshot_shadow,
        plan,
    ):
        return PositionMetricsFetchedResult.from_plan(
            projected_metrics=projected_metrics,
            plan=plan,
            snapshot_shadow=snapshot_shadow,
        )
