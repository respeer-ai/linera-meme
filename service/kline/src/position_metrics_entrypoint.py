class PositionMetricsEntrypoint:
    def __init__(
        self,
        *,
        payload_planner,
        payload_enricher,
    ):
        self.payload_planner = payload_planner
        self.payload_enricher = payload_enricher

    def enrich_position_metrics_from_payload(
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
    ):
        return self.enrich_position_metrics_from_payload_result(
            position,
            payload,
            replay_bundle=replay_bundle,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=pool_swap_count_since_open,
            pool_history_gap_summary=pool_history_gap_summary,
            position_basis_snapshot=position_basis_snapshot,
            pool_state_snapshot=pool_state_snapshot,
        ).metrics

    def enrich_position_metrics_from_payload_result(
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
    ):
        return self.payload_enricher.enrich(
            position,
            payload,
            replay_bundle=replay_bundle,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=pool_swap_count_since_open,
            pool_history_gap_summary=pool_history_gap_summary,
            position_basis_snapshot=position_basis_snapshot,
            pool_state_snapshot=pool_state_snapshot,
        )

    def plan_position_metrics_from_payload(
        self,
        position: dict,
        payload: dict,
    ):
        return self.payload_planner.plan(
            position,
            payload,
        )
