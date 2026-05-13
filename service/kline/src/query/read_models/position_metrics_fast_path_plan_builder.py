from query.read_models.position_metrics_fetch_plan import PositionMetricsFetchPlan


class PositionMetricsFastPathPlanBuilder:
    def __init__(self, *, snapshot_fast_path=None):
        self.snapshot_fast_path = snapshot_fast_path

    def build(
        self,
        *,
        fetch_context,
    ) -> PositionMetricsFetchPlan | None:
        if self.snapshot_fast_path is None:
            return None
        fast_path_payload = self.snapshot_fast_path.resolve(**fetch_context.fetch_inputs().fast_path_kwargs())
        if fast_path_payload is None:
            return None
        return PositionMetricsFetchPlan.snapshot_fast_path(fast_path_payload)
