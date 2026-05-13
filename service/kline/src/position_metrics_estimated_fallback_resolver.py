class PositionMetricsEstimatedFallbackResolver:
    def __init__(
        self,
        *,
        build_estimated_metrics_from_liquidity_history,
    ):
        self.build_estimated_metrics_from_liquidity_history = build_estimated_metrics_from_liquidity_history

    def resolve(
        self,
        partial_metrics: dict,
        *,
        blockers: list[str],
        liquidity_history: list[dict],
        pool_transaction_history: list[dict] | None,
        current_liquidity,
        history_liquidity,
    ) -> dict:
        partial_metrics = self.build_estimated_metrics_from_liquidity_history(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            current_liquidity=current_liquidity,
            history_liquidity=history_liquidity,
        )
        partial_metrics['computation_blockers'] = list(blockers)
        return partial_metrics
