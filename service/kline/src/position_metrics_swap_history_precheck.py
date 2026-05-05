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
        live_liquidity = self.to_decimal(partial_metrics['position_liquidity_live'])
        total_supply = self.to_decimal(partial_metrics['total_supply_live'])
        redeemable_amount0 = self.to_decimal(partial_metrics['redeemable_amount0'])
        redeemable_amount1 = self.to_decimal(partial_metrics['redeemable_amount1'])
        history_liquidity = self.history_liquidity(liquidity_history)

        if redeemable_amount0 is None or redeemable_amount1 is None:
            return None, ['missing_live_redeemable_amounts']
        if live_liquidity is None or total_supply is None:
            return None, ['missing_live_liquidity_or_total_supply']
        if not liquidity_history:
            return None, ['missing_liquidity_history']

        return {
            'live_liquidity': live_liquidity,
            'total_supply': total_supply,
            'redeemable_amount0': redeemable_amount0,
            'redeemable_amount1': redeemable_amount1,
            'history_liquidity': history_liquidity,
        }, []
