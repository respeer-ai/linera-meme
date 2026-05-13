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
            'metrics': [
                self._public_metric(metric)
                for metric in self.metrics
            ],
        }

    def _public_metric(self, metric: dict) -> dict:
        public_metric = dict(metric)
        public_metric.pop('owner_receives_protocol_fees', None)
        public_metric.pop('metrics_status', None)
        public_metric.pop('fee_calculation_complete', None)
        public_metric.pop('principal_calculation_complete', None)
        if 'current_total_supply' in public_metric:
            public_metric['total_supply'] = public_metric.pop('current_total_supply')
        if 'exact_share_ratio' in public_metric:
            public_metric['share_ratio'] = public_metric.pop('exact_share_ratio')
        return public_metric
