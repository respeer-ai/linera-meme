from decimal import Decimal


class PositionMetricsHistoryEnricher:
    def __init__(
        self,
        *,
        to_decimal,
        history_liquidity,
        try_enrich_metrics_with_swap_history,
        serialize_decimal,
        build_estimated_metrics_from_liquidity_history,
    ):
        self.to_decimal = to_decimal
        self.history_liquidity = history_liquidity
        self.try_enrich_metrics_with_swap_history = try_enrich_metrics_with_swap_history
        self.serialize_decimal = serialize_decimal
        self.build_estimated_metrics_from_liquidity_history = build_estimated_metrics_from_liquidity_history

    def enrich(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict] | None,
        pool_transaction_history: list[dict] | None,
        pool_swap_count_since_open: int | None,
        owner_is_fee_to: bool,
    ) -> dict:
        blockers = list(partial_metrics['computation_blockers'])
        liquidity_history = liquidity_history or []

        if not liquidity_history:
            blockers.append('missing_liquidity_history')
            partial_metrics['computation_blockers'] = blockers
            return partial_metrics

        live_liquidity = self.to_decimal(partial_metrics['position_liquidity_live'])
        history_liquidity = self.history_liquidity(liquidity_history)
        if live_liquidity is None:
            blockers.append('missing_live_liquidity')
        elif abs(live_liquidity - history_liquidity) > Decimal('0.000000000001'):
            blockers.append('liquidity_history_mismatch')

        swap_count = int(pool_swap_count_since_open or 0)
        has_pool_swap_history = any(
            tx.get('transaction_type') in {'BuyToken0', 'SellToken0'}
            for tx in (pool_transaction_history or [])
        )
        if swap_count > 0 or has_pool_swap_history:
            exact_metrics, swap_blockers = self.try_enrich_metrics_with_swap_history(
                partial_metrics,
                liquidity_history=liquidity_history,
                pool_transaction_history=pool_transaction_history,
                owner_is_fee_to=owner_is_fee_to,
            )
            if exact_metrics is not None:
                return exact_metrics
            blockers.append('pool_has_swap_history_after_position_open')
            blockers.extend(swap_blockers)
            if 'uniswap_v2_fee_split_not_supported_yet' not in blockers:
                blockers.append('uniswap_v2_fee_split_not_supported_yet')

        redeemable_amount0 = self.to_decimal(partial_metrics['redeemable_amount0'])
        redeemable_amount1 = self.to_decimal(partial_metrics['redeemable_amount1'])
        if redeemable_amount0 is None or redeemable_amount1 is None:
            blockers.append('missing_live_redeemable_amounts')

        if not blockers:
            partial_metrics['metrics_status'] = 'exact_no_swap_history'
            partial_metrics['exact_fee_supported'] = True
            partial_metrics['exact_principal_supported'] = True
            partial_metrics['principal_amount0'] = self.serialize_decimal(redeemable_amount0)
            partial_metrics['principal_amount1'] = self.serialize_decimal(redeemable_amount1)
            partial_metrics['fee_amount0'] = '0'
            partial_metrics['fee_amount1'] = '0'
            partial_metrics['protocol_fee_amount0'] = '0'
            partial_metrics['protocol_fee_amount1'] = '0'
        else:
            partial_metrics = self.build_estimated_metrics_from_liquidity_history(
                partial_metrics,
                liquidity_history=liquidity_history,
                pool_transaction_history=pool_transaction_history,
                live_liquidity=live_liquidity,
                history_liquidity=history_liquidity,
            )

        partial_metrics['computation_blockers'] = blockers
        return partial_metrics
