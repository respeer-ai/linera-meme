from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult


class PositionMetricsPayloadOnlyExecutor:
    def execute(
        self,
        *,
        plan,
    ):
        return PositionMetricsFetchedResult.from_plan(
            live_metrics=plan.resolved_live_metrics(),
            plan=plan,
        )
