class PositionMetricsFeeFreeOpenStateSimulator:
    def __init__(
        self,
        *,
        to_attos,
    ):
        self.to_attos = to_attos

    def simulate(
        self,
        states: list[dict],
        pool_transaction_history: list[dict],
        start_index: int,
    ) -> tuple[dict, list[str]]:
        reserve0 = states[start_index]['reserve0_after']
        reserve1 = states[start_index]['reserve1_after']
        blockers = []

        for tx in pool_transaction_history[start_index + 1:]:
            tx_type = tx.get('transaction_type')
            if tx_type == 'BuyToken0':
                amount1_in = self.to_attos(tx.get('amount_1_in')) or 0
                if amount1_in <= 0:
                    blockers.append('pool_history_contains_invalid_swap_amounts')
                    continue
                amount0_out = amount1_in * reserve0 // (reserve1 + amount1_in)
                reserve1 += amount1_in
                reserve0 -= amount0_out
            elif tx_type == 'SellToken0':
                amount0_in = self.to_attos(tx.get('amount_0_in')) or 0
                if amount0_in <= 0:
                    blockers.append('pool_history_contains_invalid_swap_amounts')
                    continue
                amount1_out = amount0_in * reserve1 // (reserve0 + amount0_in)
                reserve0 += amount0_in
                reserve1 -= amount1_out
            elif tx_type in {'AddLiquidity', 'RemoveLiquidity'}:
                blockers.append('pool_has_liquidity_changes_after_position_open')
            else:
                blockers.append('pool_history_contains_unknown_transaction_type')

        return {
            'reserve0': reserve0,
            'reserve1': reserve1,
        }, sorted(set(blockers))
