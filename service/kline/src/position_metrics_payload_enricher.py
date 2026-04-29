from decimal import Decimal


class PositionMetricsPayloadEnricher:
    def __init__(
        self,
        *,
        live_history_reconciler,
        build_partial_metrics,
        enrich_metrics_with_history,
        apply_data_quality_warnings,
        account_payload_to_string,
    ):
        self.live_history_reconciler = live_history_reconciler
        self.build_partial_metrics = build_partial_metrics
        self.enrich_metrics_with_history = enrich_metrics_with_history
        self.apply_data_quality_warnings = apply_data_quality_warnings
        self.account_payload_to_string = account_payload_to_string

    def enrich(
        self,
        position: dict,
        payload: dict,
        *,
        liquidity_history: list[dict] | None = None,
        pool_transaction_history: list[dict] | None = None,
        pool_swap_count_since_open: int | None = None,
        pool_history_gap_summary: dict | None = None,
        position_basis_snapshot: dict | None = None,
        pool_state_snapshot: dict | None = None,
    ) -> dict:
        data = payload['data']
        live_history = self.live_history_reconciler.reconcile(
            position=position,
            payload_data=data,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=pool_swap_count_since_open,
            pool_history_gap_summary=pool_history_gap_summary,
        )
        liquidity_history = live_history['liquidity_history']
        pool_transaction_history = live_history['pool_transaction_history']
        pool_swap_count_since_open = live_history['pool_swap_count_since_open']
        pool_history_gap_summary = live_history['pool_history_gap_summary']

        liquidity = data.get('liquidity') or {}
        liquidity_value = liquidity.get('liquidity')
        total_supply_value = data.get('totalSupply')
        virtual_initial_liquidity = bool(data.get('virtualInitialLiquidity'))
        owner_is_fee_to = (
            self.account_payload_to_string((data.get('pool') or {}).get('fee_to')) == position['owner']
        )
        partial_metrics = self.build_partial_metrics(
            liquidity,
            total_supply_value,
            virtual_initial_liquidity,
        )

        if liquidity_value is not None and total_supply_value not in (None, '0'):
            partial_metrics['exact_share_ratio'] = str(
                (Decimal(str(liquidity_value)) / Decimal(str(total_supply_value))).normalize()
            )
        partial_metrics['owner_is_fee_to'] = owner_is_fee_to

        metrics = self.enrich_metrics_with_history(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=pool_swap_count_since_open,
            owner_is_fee_to=owner_is_fee_to,
        )
        return self.apply_data_quality_warnings(
            metrics,
            pool_history_gap_summary=pool_history_gap_summary,
        )
