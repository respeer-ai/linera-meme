class PositionMetricsReadResult:
    def __init__(
        self,
        *,
        owner: str,
        metrics: list[dict],
        metric_diagnostics: list[dict] | None = None,
        shadow_diagnostics: list[dict] | None = None,
    ):
        self.owner = owner
        self.metrics = list(metrics)
        self.metric_diagnostics = list(metric_diagnostics or [])
        self.shadow_diagnostics = list(shadow_diagnostics or [])

    def public_payload(self) -> dict:
        return {
            'owner': self.owner,
            'metrics': list(self.metrics),
        }
