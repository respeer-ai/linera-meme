class PositionMetricsNoopDiagnosticRecorder:
    def record_inexact_metric(self, _metric: dict) -> None:
        return None

    def record_snapshot_shadow(self, _diagnostic: dict) -> None:
        return None
