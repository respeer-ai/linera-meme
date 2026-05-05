from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult


class PositionMetricsReplayFallbackResultBuilder:
    def build(
        self,
        *,
        live_metrics: dict,
        snapshot_shadow,
        plan,
    ):
        return PositionMetricsFetchedResult.from_plan(
            live_metrics=live_metrics,
            plan=plan,
            snapshot_shadow=snapshot_shadow,
        )
