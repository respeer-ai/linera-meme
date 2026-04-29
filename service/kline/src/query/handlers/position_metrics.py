class PositionMetricsHandler:
    def __init__(self, read_model, serializer, diagnostic_recorder):
        self.read_model = read_model
        self.serializer = serializer
        self.diagnostic_recorder = diagnostic_recorder

    async def get_position_metrics(self, **kwargs):
        payload = await self.read_model.get_position_metrics(**kwargs)
        shadow_diagnostics = list(payload.pop('_shadow_diagnostics', []) or [])
        self._record_inexact_metrics(payload)
        self._record_shadow_diagnostics(shadow_diagnostics)
        return self.serializer.serialize_position_metrics(payload)

    def _record_inexact_metrics(self, payload: dict):
        for metric in payload.get('metrics') or []:
            if not self._should_record(metric):
                continue
            self.diagnostic_recorder.record_inexact_metric(metric)

    def _should_record(self, metric: dict) -> bool:
        return (
            not bool(metric.get('exact_fee_supported'))
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
