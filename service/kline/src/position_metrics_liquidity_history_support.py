class PositionMetricsLiquidityHistorySupport:
    def __init__(
        self,
        *,
        analyzer_factory,
    ):
        self.analyzer_factory = analyzer_factory

    def history_liquidity(self, liquidity_history: list[dict]):
        return self.analyzer_factory().history_liquidity(liquidity_history)

    def latest_position_liquidity_tx(self, liquidity_history: list[dict]):
        return self.analyzer_factory().latest_position_liquidity_tx(liquidity_history)

    def build_observed_swap_fee_estimate(
        self,
        *,
        pool_transaction_history: list[dict] | None,
        latest_position_tx: dict | None,
        liquidity_basis,
        total_supply_live,
    ):
        return self.analyzer_factory().build_observed_swap_fee_estimate(
            pool_transaction_history=pool_transaction_history,
            latest_position_tx=latest_position_tx,
            liquidity_basis=liquidity_basis,
            total_supply_live=total_supply_live,
        )

    def build_estimated_metrics_from_liquidity_history(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict],
        pool_transaction_history: list[dict] | None,
        live_liquidity,
        history_liquidity,
    ):
        return self.analyzer_factory().build_estimated_metrics_from_liquidity_history(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            live_liquidity=live_liquidity,
            history_liquidity=history_liquidity,
        )

    def history_liquidity_before(
        self,
        liquidity_history: list[dict],
        latest_position_tx: dict,
    ):
        return self.analyzer_factory().history_liquidity_before(
            liquidity_history,
            latest_position_tx,
        )
