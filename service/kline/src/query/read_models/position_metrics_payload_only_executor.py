from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult


class PositionMetricsPayloadOnlyExecutor:
    def execute(
        self,
        *,
        plan,
    ):
        return PositionMetricsFetchedResult.from_plan(
            projected_metrics=plan.resolved_projected_metrics(),
            plan=plan,
        )
