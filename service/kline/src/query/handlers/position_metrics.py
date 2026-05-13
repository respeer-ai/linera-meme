class PositionMetricsHandler:
    def __init__(self, read_model, diagnostic_recorder):
        self.read_model = read_model
        self.diagnostic_recorder = diagnostic_recorder

    async def get_position_metrics(self, **kwargs):
        read_result = await self.read_model.get_position_metrics(**kwargs)
        payload = read_result.public_payload()
        self._record_inexact_metrics(read_result.metric_diagnostics)
        self._record_shadow_diagnostics(read_result.shadow_diagnostics)
        return dict(payload)

    def _record_inexact_metrics(self, metrics: list[dict]) -> None:
        for metric in metrics:
            if not self._should_record(metric):
                continue
            self.diagnostic_recorder.record_inexact_metric(metric)

    def _should_record(self, metric: dict) -> bool:
        return (
            not bool(metric.get('fee_calculation_complete'))
            or bool(metric.get('computation_blockers'))
            or bool(metric.get('value_warning_codes'))
        )

    def _record_shadow_diagnostics(self, diagnostics: list[dict]) -> None:
        for diagnostic in diagnostics:
            if not self._should_record_shadow(diagnostic):
                continue
            self.diagnostic_recorder.record_snapshot_shadow(diagnostic)

    def _should_record_shadow(self, diagnostic: dict) -> bool:
        shadow = diagnostic.get('snapshot_shadow') or {}
        return str(shadow.get('readiness') or '') != 'candidate'
