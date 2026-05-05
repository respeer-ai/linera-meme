from query.read_models.position_metrics_fetch_stage import PositionMetricsFetchStage
from position_metrics_payload_decision import PositionMetricsPayloadDecision


class PositionMetricsPayloadResult:
    def __init__(
        self,
        *,
        metrics: dict,
        decision: str,
        reason_code: str,
    ):
        self.metrics = dict(metrics)
        self.decision = decision
        self.reason_code = reason_code

    def fetch_stage(self) -> str:
        if self.decision == PositionMetricsPayloadDecision.PAYLOAD_ONLY:
            return PositionMetricsFetchStage.PAYLOAD_ONLY
        return PositionMetricsFetchStage.REPLAY_FALLBACK

    def needs_replay_assembly(self) -> bool:
        return self.fetch_stage() == PositionMetricsFetchStage.REPLAY_FALLBACK
