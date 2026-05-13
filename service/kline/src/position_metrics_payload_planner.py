from position_metrics_payload_result import PositionMetricsPayloadResult


class PositionMetricsPayloadPlanner:
    def __init__(
        self,
        *,
        payload_semantic_builder,
        payload_decision_resolver,
        apply_data_quality_warnings,
        build_transaction_gap_summary,
    ):
        self.payload_semantic_builder = payload_semantic_builder
        self.payload_decision_resolver = payload_decision_resolver
        self.apply_data_quality_warnings = apply_data_quality_warnings
        self.build_transaction_gap_summary = build_transaction_gap_summary

    def plan(
        self,
        position: dict,
        payload: dict,
        *,
        liquidity_history: list[dict] | None = None,
        pool_transaction_history: list[dict] | None = None,
        pool_swap_count_since_open: int | None = None,
        pool_history_gap_summary: dict | None = None,
    ) -> PositionMetricsPayloadResult:
        data = payload['data']
        if pool_history_gap_summary is None and pool_transaction_history is not None:
            pool_history_gap_summary = self.build_transaction_gap_summary(pool_transaction_history)
        partial_metrics = self.payload_semantic_builder.build(
            position=position,
            payload_data=data,
        )
        payload_decision = self.payload_decision_resolver.resolve(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=pool_swap_count_since_open,
        )
        if payload_decision.is_payload_only():
            return PositionMetricsPayloadResult(
                metrics=self.apply_data_quality_warnings(
                    payload_decision.metrics,
                    pool_history_gap_summary=pool_history_gap_summary,
                ),
                decision=payload_decision.decision,
                reason_code=payload_decision.reason_code,
            )
        return PositionMetricsPayloadResult(
            metrics=payload_decision.metrics,
            decision=payload_decision.decision,
            reason_code=payload_decision.reason_code,
        )
