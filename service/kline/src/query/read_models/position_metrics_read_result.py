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
        public_metric.pop('owner_is_fee_to', None)
        public_metric.pop('metrics_status', None)
        public_metric.pop('exact_fee_supported', None)
        public_metric.pop('exact_principal_supported', None)
        if 'position_liquidity_live' in public_metric:
            public_metric['position_liquidity'] = public_metric.pop('position_liquidity_live')
        if 'total_supply_live' in public_metric:
            public_metric['total_supply'] = public_metric.pop('total_supply_live')
        if 'exact_share_ratio' in public_metric:
            public_metric['share_ratio'] = public_metric.pop('exact_share_ratio')
        return public_metric
