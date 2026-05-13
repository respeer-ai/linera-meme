class PositionMetricsFetchedResult:
    def __init__(
        self,
        *,
        projected_metrics: dict,
        fetch_stage: str | None = None,
        fetch_reason_code: str | None = None,
        snapshot_shadow: dict | None = None,
    ):
        self.projected_metrics = dict(projected_metrics)
        self.fetch_stage = fetch_stage
        self.fetch_reason_code = fetch_reason_code
        self.snapshot_shadow = snapshot_shadow

    @classmethod
    def from_fetcher_payload(cls, fetched):
        if isinstance(fetched, cls):
            return fetched
        if not isinstance(fetched, dict):
            return cls(projected_metrics=fetched)
        if 'projected_metrics' not in fetched:
            return cls(projected_metrics=fetched)
        return cls(
            projected_metrics=fetched['projected_metrics'],
            fetch_stage=fetched.get('fetch_stage'),
            fetch_reason_code=fetched.get('fetch_reason_code'),
            snapshot_shadow=fetched.get('snapshot_shadow'),
        )

    @classmethod
    def from_plan(
        cls,
        *,
        projected_metrics: dict,
        plan,
        snapshot_shadow: dict | None = None,
    ):
        return cls(
            projected_metrics=projected_metrics,
            fetch_stage=plan.resolved_fetch_stage(),
            fetch_reason_code=plan.resolved_fetch_reason_code(),
            snapshot_shadow=snapshot_shadow,
        )
