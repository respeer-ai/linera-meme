class PositionMetricsHistoryEvaluation:
    def __init__(
        self,
        *,
        partial_metrics: dict,
        blockers: list[str],
        liquidity_history: list[dict],
        pool_transaction_history: list[dict] | None,
        current_liquidity,
        history_liquidity,
        redeemable_amount0,
        redeemable_amount1,
        swap_exact_metrics: dict | None,
        swap_blockers: list[str],
        has_pool_swap_history: bool,
    ):
        self.partial_metrics = partial_metrics
        self.blockers = list(blockers)
        self.liquidity_history = liquidity_history
        self.pool_transaction_history = pool_transaction_history
        self.current_liquidity = current_liquidity
        self.history_liquidity = history_liquidity
        self.redeemable_amount0 = redeemable_amount0
        self.redeemable_amount1 = redeemable_amount1
        self.swap_exact_metrics = swap_exact_metrics
        self.swap_blockers = list(swap_blockers)
        self.has_pool_swap_history = bool(has_pool_swap_history)

    def as_kwargs(self) -> dict:
        return {
            'partial_metrics': self.partial_metrics,
            'blockers': list(self.blockers),
            'liquidity_history': self.liquidity_history,
            'pool_transaction_history': self.pool_transaction_history,
            'current_liquidity': self.current_liquidity,
            'history_liquidity': self.history_liquidity,
            'redeemable_amount0': self.redeemable_amount0,
            'redeemable_amount1': self.redeemable_amount1,
            'swap_exact_metrics': self.swap_exact_metrics,
            'swap_blockers': list(self.swap_blockers),
            'has_pool_swap_history': self.has_pool_swap_history,
        }
