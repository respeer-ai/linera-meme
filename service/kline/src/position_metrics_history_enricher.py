from decimal import Decimal
from position_metrics_history_evaluation import PositionMetricsHistoryEvaluation


class PositionMetricsHistoryEnricher:
    def __init__(
        self,
        *,
        to_decimal,
        history_liquidity,
        try_enrich_metrics_with_swap_history,
        semantic_resolver,
    ):
        self.to_decimal = to_decimal
        self.history_liquidity = history_liquidity
        self.try_enrich_metrics_with_swap_history = try_enrich_metrics_with_swap_history
        self.semantic_resolver = semantic_resolver

    def enrich(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict] | None,
        pool_transaction_history: list[dict] | None,
        pool_swap_count_since_open: int | None,
        owner_receives_protocol_fees: bool,
    ) -> dict:
        blockers = list(partial_metrics['computation_blockers'])
        liquidity_history = liquidity_history or []

        if not liquidity_history:
            blockers.append('missing_liquidity_history')
            return self.semantic_resolver.resolve(
                PositionMetricsHistoryEvaluation(
                    partial_metrics=partial_metrics,
                    blockers=blockers,
                    liquidity_history=liquidity_history,
                    pool_transaction_history=pool_transaction_history,
                    current_liquidity=None,
                    history_liquidity=None,
                    redeemable_amount0=None,
                    redeemable_amount1=None,
                    swap_exact_metrics=None,
                    swap_blockers=[],
                    has_pool_swap_history=False,
                ),
            )

        current_liquidity = self.to_decimal(partial_metrics['position_liquidity'])
        history_liquidity = self.history_liquidity(liquidity_history)
        if current_liquidity is None:
            blockers.append('missing_current_liquidity')
        elif abs(current_liquidity - history_liquidity) > Decimal('0.000000000001'):
            blockers.append('liquidity_history_mismatch')

        swap_count = int(pool_swap_count_since_open or 0)
        has_pool_swap_history = any(
            tx.get('transaction_type') in {'BuyToken0', 'SellToken0'}
            for tx in (pool_transaction_history or [])
        )
        swap_exact_metrics = None
        swap_blockers = []
        if swap_count > 0 or has_pool_swap_history:
            swap_exact_metrics, swap_blockers = self.try_enrich_metrics_with_swap_history(
                partial_metrics,
                liquidity_history=liquidity_history,
                pool_transaction_history=pool_transaction_history,
                owner_receives_protocol_fees=owner_receives_protocol_fees,
            )

        redeemable_amount0 = self.to_decimal(partial_metrics['redeemable_amount0'])
        redeemable_amount1 = self.to_decimal(partial_metrics['redeemable_amount1'])
        return self.semantic_resolver.resolve(
            PositionMetricsHistoryEvaluation(
                partial_metrics=partial_metrics,
                blockers=blockers,
                liquidity_history=liquidity_history,
                pool_transaction_history=pool_transaction_history,
                current_liquidity=current_liquidity,
                history_liquidity=history_liquidity,
                redeemable_amount0=redeemable_amount0,
                redeemable_amount1=redeemable_amount1,
                swap_exact_metrics=swap_exact_metrics,
                swap_blockers=swap_blockers,
                has_pool_swap_history=(swap_count > 0 or has_pool_swap_history),
            ),
        )
