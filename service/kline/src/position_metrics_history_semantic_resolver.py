class PositionMetricsHistorySemanticResolver:
    def __init__(
        self,
        *,
        no_swap_exact_resolver,
        estimated_fallback_resolver,
    ):
        self.no_swap_exact_resolver = no_swap_exact_resolver
        self.estimated_fallback_resolver = estimated_fallback_resolver

    def resolve(
        self,
        evaluation,
    ) -> dict:
        partial_metrics = evaluation.partial_metrics
        blockers = evaluation.blockers
        liquidity_history = evaluation.liquidity_history
        pool_transaction_history = evaluation.pool_transaction_history
        current_liquidity = evaluation.current_liquidity
        history_liquidity = evaluation.history_liquidity
        redeemable_amount0 = evaluation.redeemable_amount0
        redeemable_amount1 = evaluation.redeemable_amount1
        swap_exact_metrics = evaluation.swap_exact_metrics
        swap_blockers = evaluation.swap_blockers
        has_pool_swap_history = evaluation.has_pool_swap_history
        if not liquidity_history:
            partial_metrics['computation_blockers'] = list(blockers)
            return partial_metrics
        if swap_exact_metrics is not None:
            return swap_exact_metrics

        resolved_blockers = list(blockers)
        if has_pool_swap_history:
            resolved_blockers.append('pool_has_swap_history_after_position_open')
            resolved_blockers.extend(swap_blockers)
            if 'uniswap_v2_fee_split_not_supported_yet' not in resolved_blockers:
                resolved_blockers.append('uniswap_v2_fee_split_not_supported_yet')

        if redeemable_amount0 is None or redeemable_amount1 is None:
            resolved_blockers.append('missing_projected_redeemable_amounts')

        if not resolved_blockers:
            return self.no_swap_exact_resolver.resolve(
                partial_metrics,
                redeemable_amount0=redeemable_amount0,
                redeemable_amount1=redeemable_amount1,
                blockers=resolved_blockers,
            )

        return self.estimated_fallback_resolver.resolve(
            partial_metrics,
            blockers=resolved_blockers,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            current_liquidity=current_liquidity,
            history_liquidity=history_liquidity,
        )
