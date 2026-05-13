class PositionMetricsSwapHistoryPrecheck:
    def __init__(
        self,
        *,
        to_decimal,
        history_liquidity,
    ):
        self.to_decimal = to_decimal
        self.history_liquidity = history_liquidity

    def check(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict],
    ) -> tuple[dict | None, list[str]]:
        current_liquidity = self.to_decimal(partial_metrics['position_liquidity'])
        total_supply = self.to_decimal(partial_metrics['current_total_supply'])
        redeemable_amount0 = self.to_decimal(partial_metrics['redeemable_amount0'])
        redeemable_amount1 = self.to_decimal(partial_metrics['redeemable_amount1'])
        history_liquidity = self.history_liquidity(liquidity_history)

        if redeemable_amount0 is None or redeemable_amount1 is None:
            return None, ['missing_projected_redeemable_amounts']
        if current_liquidity is None or total_supply is None:
            return None, ['missing_current_liquidity_or_total_supply']
        if not liquidity_history:
            return None, ['missing_liquidity_history']

        return {
            'current_liquidity': current_liquidity,
            'total_supply': total_supply,
            'redeemable_amount0': redeemable_amount0,
            'redeemable_amount1': redeemable_amount1,
            'history_liquidity': history_liquidity,
        }, []
