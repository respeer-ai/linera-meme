from position_metrics_payload_result import PositionMetricsPayloadResult


class PositionMetricsPayloadEnricher:
    def __init__(
        self,
        *,
        payload_semantic_builder,
        payload_decision_resolver,
        enrich_metrics_with_history,
        apply_data_quality_warnings,
        build_transaction_gap_summary,
    ):
        self.payload_semantic_builder = payload_semantic_builder
        self.payload_decision_resolver = payload_decision_resolver
        self.enrich_metrics_with_history = enrich_metrics_with_history
        self.apply_data_quality_warnings = apply_data_quality_warnings
        self.build_transaction_gap_summary = build_transaction_gap_summary

    def enrich(
        self,
        position: dict,
        payload: dict,
        *,
        replay_bundle=None,
        liquidity_history: list[dict] | None = None,
        pool_transaction_history: list[dict] | None = None,
        pool_swap_count_since_open: int | None = None,
        pool_history_gap_summary: dict | None = None,
        position_basis_snapshot: dict | None = None,
        pool_state_snapshot: dict | None = None,
    ) -> PositionMetricsPayloadResult:
        data = payload['data']
        if replay_bundle is not None:
            liquidity_history = replay_bundle.liquidity_history()
            pool_transaction_history = replay_bundle.pool_transaction_history()
            pool_swap_count_since_open = replay_bundle.pool_swap_count_since_open()
            pool_history_gap_summary = replay_bundle.pool_history_gap_summary()
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
        partial_metrics = payload_decision.metrics
        if payload_decision.is_payload_only():
            return PositionMetricsPayloadResult(
                metrics=self.apply_data_quality_warnings(
                    partial_metrics,
                    pool_history_gap_summary=pool_history_gap_summary,
                ),
                decision=payload_decision.decision,
                reason_code=payload_decision.reason_code,
            )
        owner_receives_protocol_fees = bool(partial_metrics.get('owner_receives_protocol_fees'))

        metrics = self.enrich_metrics_with_history(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=pool_swap_count_since_open,
            owner_receives_protocol_fees=owner_receives_protocol_fees,
        )
        return PositionMetricsPayloadResult(
            metrics=self.apply_data_quality_warnings(
                metrics,
                pool_history_gap_summary=pool_history_gap_summary,
            ),
            decision=payload_decision.decision,
            reason_code=payload_decision.reason_code,
        )
