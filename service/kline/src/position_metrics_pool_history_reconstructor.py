class PositionMetricsPoolHistoryReconstructor:
    def __init__(
        self,
        *,
        to_attos,
        swap_expected_out_attos,
        swap_out_within_tolerance,
        infer_hidden_swap_before_batch,
        apply_recorded_swap_attos,
        sqrt_attos_product,
        mint_fee_attos,
        attos_within_tolerance,
    ):
        self.to_attos = to_attos
        self.swap_expected_out_attos = swap_expected_out_attos
        self.swap_out_within_tolerance = swap_out_within_tolerance
        self.infer_hidden_swap_before_batch = infer_hidden_swap_before_batch
        self.apply_recorded_swap_attos = apply_recorded_swap_attos
        self.sqrt_attos_product = sqrt_attos_product
        self.mint_fee_attos = mint_fee_attos
        self.attos_within_tolerance = attos_within_tolerance

    def reconstruct(
        self,
        pool_transaction_history: list[dict],
        *,
        virtual_initial_liquidity: bool,
    ) -> tuple[list[dict] | None, list[dict] | None, list[str]]:
        if not pool_transaction_history:
            return None, None, ['missing_pool_transaction_history']

        reserve0 = 0
        reserve1 = 0
        total_supply = 0
        k_last = 0
        states = []
        effective_history = []
        blockers = []
        index = 0

        while index < len(pool_transaction_history):
            tx = pool_transaction_history[index]
            tx_type = tx.get('transaction_type')
            amount0_in = self.to_attos(tx.get('amount_0_in')) or 0
            amount0_out = self.to_attos(tx.get('amount_0_out')) or 0
            amount1_in = self.to_attos(tx.get('amount_1_in')) or 0
            amount1_out = self.to_attos(tx.get('amount_1_out')) or 0
            liquidity = self.to_attos(tx.get('liquidity')) or 0
            protocol_fee_minted = 0

            if tx_type in {'BuyToken0', 'SellToken0'}:
                expected_out = self.swap_expected_out_attos(
                    tx_type,
                    reserve0,
                    reserve1,
                    amount0_in,
                    amount1_in,
                )
                recorded_out = amount0_out if tx_type == 'BuyToken0' else amount1_out
                if expected_out is None or not self.swap_out_within_tolerance(expected_out, recorded_out):
                    hidden_swap = self.infer_hidden_swap_before_batch(
                        reserve0,
                        reserve1,
                        pool_transaction_history,
                        index,
                    )
                    if hidden_swap is None:
                        blockers.append('pool_history_contains_invalid_swap_amounts')
                        break
                    hidden_type = hidden_swap.get('transaction_type')
                    reserve0, reserve1 = self.apply_recorded_swap_attos(
                        hidden_type,
                        reserve0,
                        reserve1,
                        amount0_in=self.to_attos(hidden_swap.get('amount_0_in')) or 0,
                        amount0_out=self.to_attos(hidden_swap.get('amount_0_out')) or 0,
                        amount1_in=self.to_attos(hidden_swap.get('amount_1_in')) or 0,
                        amount1_out=self.to_attos(hidden_swap.get('amount_1_out')) or 0,
                    )
                    effective_history.append(hidden_swap)
                    states.append({
                        'transaction_id': hidden_swap.get('transaction_id'),
                        'created_at': hidden_swap.get('created_at'),
                        'transaction_type': hidden_type,
                        'from_account': hidden_swap.get('from_account'),
                        'reserve0_after': reserve0,
                        'reserve1_after': reserve1,
                        'total_supply_after': total_supply,
                        'k_last_after': k_last,
                        'protocol_fee_minted_after': 0,
                    })
                    expected_out = self.swap_expected_out_attos(
                        tx_type,
                        reserve0,
                        reserve1,
                        amount0_in,
                        amount1_in,
                    )
                    if expected_out is None or not self.swap_out_within_tolerance(expected_out, recorded_out):
                        blockers.append('pool_history_contains_invalid_swap_amounts')
                        break

            if tx_type == 'AddLiquidity':
                if reserve0 == 0 and reserve1 == 0:
                    expected_liquidity = self.sqrt_attos_product(amount0_in, amount1_in)
                    if expected_liquidity is None:
                        blockers.append('pool_history_bootstrap_supply_unknown')
                        break
                    if virtual_initial_liquidity:
                        if liquidity not in (0, expected_liquidity):
                            blockers.append('pool_history_bootstrap_supply_unknown')
                            break
                        total_supply = expected_liquidity
                    else:
                        if liquidity != expected_liquidity:
                            blockers.append('pool_history_bootstrap_supply_unknown')
                            break
                        total_supply = liquidity
                    reserve0 += amount0_in
                    reserve1 += amount1_in
                    k_last = self.sqrt_attos_product(reserve0, reserve1) or 0
                else:
                    fee_share = self.mint_fee_attos(total_supply, reserve0, reserve1, k_last)
                    protocol_fee_minted = fee_share
                    total_supply += fee_share
                    expected_liquidity = min(
                        amount0_in * total_supply // reserve0,
                        amount1_in * total_supply // reserve1,
                    )
                    if not self.attos_within_tolerance(liquidity, expected_liquidity):
                        blockers.append('pool_history_liquidity_mint_mismatch')
                        break
                    total_supply += liquidity
                    reserve0 += amount0_in
                    reserve1 += amount1_in
                    k_last = self.sqrt_attos_product(reserve0, reserve1) or 0
            elif tx_type == 'RemoveLiquidity':
                fee_share = self.mint_fee_attos(total_supply, reserve0, reserve1, k_last)
                protocol_fee_minted = fee_share
                total_supply += fee_share
                if liquidity > total_supply or amount0_out > reserve0 or amount1_out > reserve1:
                    blockers.append('pool_history_remove_liquidity_invalid')
                    break
                total_supply -= liquidity
                reserve0 -= amount0_out
                reserve1 -= amount1_out
                k_last = self.sqrt_attos_product(reserve0, reserve1) or 0
            elif tx_type in {'BuyToken0', 'SellToken0'}:
                reserve0, reserve1 = self.apply_recorded_swap_attos(
                    tx_type,
                    reserve0,
                    reserve1,
                    amount0_in=amount0_in,
                    amount0_out=amount0_out,
                    amount1_in=amount1_in,
                    amount1_out=amount1_out,
                )
                if reserve0 < 0 or reserve1 < 0:
                    blockers.append('pool_history_contains_invalid_swap_amounts')
                    break
            else:
                blockers.append('pool_history_contains_unknown_transaction_type')
                break

            effective_history.append(tx)
            states.append({
                'transaction_id': tx.get('transaction_id'),
                'created_at': tx.get('created_at'),
                'transaction_type': tx_type,
                'from_account': tx.get('from_account'),
                'reserve0_after': reserve0,
                'reserve1_after': reserve1,
                'total_supply_after': total_supply,
                'k_last_after': k_last,
                'protocol_fee_minted_after': protocol_fee_minted,
            })
            index += 1

        if blockers:
            return None, None, sorted(set(blockers))
        return effective_history, states, []
