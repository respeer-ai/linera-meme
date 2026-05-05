class PositionMetricsPayloadDecisionResult:
    def __init__(
        self,
        *,
        decision: str,
        reason_code: str,
        metrics: dict,
    ):
        self.decision = decision
        self.reason_code = reason_code
        self.metrics = dict(metrics)

    def is_payload_only(self) -> bool:
        return self.decision == 'payload_only'
