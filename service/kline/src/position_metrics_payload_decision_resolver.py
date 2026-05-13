from position_metrics_payload_decision import PositionMetricsPayloadDecision
from position_metrics_payload_decision_result import PositionMetricsPayloadDecisionResult


class PositionMetricsPayloadDecisionResolver:
    PAYLOAD_ONLY_REASON_CODE = 'payload_history_unavailable'
    NEEDS_HISTORY_ENRICHMENT_REASON_CODE = 'payload_requires_history'

    def resolve(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict] | None,
        pool_transaction_history: list[dict] | None,
        pool_swap_count_since_open: int | None,
    ):
        if liquidity_history is None and pool_transaction_history is None and pool_swap_count_since_open is None:
            return PositionMetricsPayloadDecisionResult(
                decision=PositionMetricsPayloadDecision.PAYLOAD_ONLY,
                reason_code=self.PAYLOAD_ONLY_REASON_CODE,
                metrics=partial_metrics,
            )
        return PositionMetricsPayloadDecisionResult(
            decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
            reason_code=self.NEEDS_HISTORY_ENRICHMENT_REASON_CODE,
            metrics=partial_metrics,
        )
