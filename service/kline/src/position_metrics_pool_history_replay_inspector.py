class PositionMetricsPoolHistoryReplayInspector:
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
        serialize_attos_debug,
    ):
        self.to_attos = to_attos
        self.swap_expected_out_attos = swap_expected_out_attos
        self.swap_out_within_tolerance = swap_out_within_tolerance
        self.infer_hidden_swap_before_batch = infer_hidden_swap_before_batch
        self.apply_recorded_swap_attos = apply_recorded_swap_attos
        self.sqrt_attos_product = sqrt_attos_product
        self.mint_fee_attos = mint_fee_attos
        self.attos_within_tolerance = attos_within_tolerance
        self.serialize_attos_debug = serialize_attos_debug

    def inspect(
        self,
        pool_transaction_history: list[dict],
        *,
        virtual_initial_liquidity: bool,
        swap_out_tolerance_attos: int,
    ) -> dict:
        if not pool_transaction_history:
            return {
                'ok': False,
                'processed_count': 0,
                'blockers': ['missing_pool_transaction_history'],
                'first_failure': {
                    'reason': 'missing_pool_transaction_history',
                },
            }

        reserve0 = 0
        reserve1 = 0
        total_supply = 0
        k_last = 0
        processed_count = 0

        def failure(reason: str, tx: dict | None = None, **fields):
            failure_payload = {
                'reason': reason,
                'reserve0_attos_before': self.serialize_attos_debug(reserve0),
                'reserve1_attos_before': self.serialize_attos_debug(reserve1),
                'total_supply_attos_before': self.serialize_attos_debug(total_supply),
                'k_last_before': self.serialize_attos_debug(k_last),
            }
            if tx is not None:
                failure_payload.update({
                    'transaction_id': tx.get('transaction_id'),
                    'transaction_type': tx.get('transaction_type'),
                    'created_at': tx.get('created_at'),
                    'from_account': tx.get('from_account'),
                })
            for key, value in fields.items():
                if isinstance(value, int):
                    failure_payload[key] = self.serialize_attos_debug(value)
                else:
                    failure_payload[key] = value
            return {
                'ok': False,
                'processed_count': processed_count,
                'blockers': [reason],
                'first_failure': failure_payload,
            }

        index = 0
        while index < len(pool_transaction_history):
            tx = pool_transaction_history[index]
            tx_type = tx.get('transaction_type')
            amount0_in = self.to_attos(tx.get('amount_0_in')) or 0
            amount0_out = self.to_attos(tx.get('amount_0_out')) or 0
            amount1_in = self.to_attos(tx.get('amount_1_in')) or 0
            amount1_out = self.to_attos(tx.get('amount_1_out')) or 0
            liquidity = self.to_attos(tx.get('liquidity')) or 0

            if tx_type in {'BuyToken0', 'SellToken0'}:
                expected_out = self.swap_expected_out_attos(
                    tx_type,
                    reserve0,
                    reserve1,
                    amount0_in,
                    amount1_in,
                )
                recorded_out = amount0_out if tx_type == 'BuyToken0' else amount1_out
                if expected_out is None or not self.swap_out_within_tolerance(
                    expected_out,
                    recorded_out,
                    tolerance=swap_out_tolerance_attos,
                ):
                    hidden_swap = self.infer_hidden_swap_before_batch(
                        reserve0,
                        reserve1,
                        pool_transaction_history,
                        index,
                    )
                    if hidden_swap is not None:
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
                        expected_out = self.swap_expected_out_attos(
                            tx_type,
                            reserve0,
                            reserve1,
                            amount0_in,
                            amount1_in,
                        )
                    if expected_out is None or not self.swap_out_within_tolerance(
                        expected_out,
                        recorded_out,
                        tolerance=swap_out_tolerance_attos,
                    ):
                        return failure(
                            'pool_history_contains_invalid_swap_amounts',
                            tx,
                            expected_out_attos=expected_out,
                            recorded_out_attos=recorded_out,
                            swap_out_tolerance_attos=swap_out_tolerance_attos,
                            hidden_swap_inferred=hidden_swap is not None,
                        )

            if tx_type == 'AddLiquidity':
                if reserve0 == 0 and reserve1 == 0:
                    expected_liquidity = self.sqrt_attos_product(amount0_in, amount1_in)
                    if expected_liquidity is None:
                        return failure('pool_history_bootstrap_supply_unknown', tx)
                    if virtual_initial_liquidity:
                        if liquidity != 0:
                            return failure(
                                'pool_history_bootstrap_supply_unknown',
                                tx,
                                expected_liquidity_attos=expected_liquidity,
                                recorded_liquidity_attos=liquidity,
                            )
                        total_supply = expected_liquidity
                    else:
                        if liquidity != expected_liquidity:
                            return failure(
                                'pool_history_bootstrap_supply_unknown',
                                tx,
                                expected_liquidity_attos=expected_liquidity,
                                recorded_liquidity_attos=liquidity,
                            )
                        total_supply = liquidity
                    reserve0 += amount0_in
                    reserve1 += amount1_in
                    k_last = self.sqrt_attos_product(reserve0, reserve1) or 0
                else:
                    fee_share = self.mint_fee_attos(total_supply, reserve0, reserve1, k_last)
                    total_supply += fee_share
                    expected_liquidity = min(
                        amount0_in * total_supply // reserve0,
                        amount1_in * total_supply // reserve1,
                    )
                    if not self.attos_within_tolerance(liquidity, expected_liquidity):
                        return failure(
                            'pool_history_liquidity_mint_mismatch',
                            tx,
                            fee_share_attos=fee_share,
                            expected_liquidity_attos=expected_liquidity,
                            recorded_liquidity_attos=liquidity,
                        )
                    total_supply += liquidity
                    reserve0 += amount0_in
                    reserve1 += amount1_in
                    k_last = self.sqrt_attos_product(reserve0, reserve1) or 0
            elif tx_type == 'RemoveLiquidity':
                fee_share = self.mint_fee_attos(total_supply, reserve0, reserve1, k_last)
                total_supply += fee_share
                if liquidity > total_supply or amount0_out > reserve0 or amount1_out > reserve1:
                    return failure(
                        'pool_history_remove_liquidity_invalid',
                        tx,
                        fee_share_attos=fee_share,
                        recorded_liquidity_attos=liquidity,
                        amount0_out_attos=amount0_out,
                        amount1_out_attos=amount1_out,
                    )
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
                    return failure('pool_history_contains_invalid_swap_amounts', tx)
            else:
                return failure('pool_history_contains_unknown_transaction_type', tx)

            processed_count += 1
            index += 1

        return {
            'ok': True,
            'processed_count': processed_count,
            'blockers': [],
            'first_failure': None,
            'swap_out_tolerance_attos': self.serialize_attos_debug(swap_out_tolerance_attos),
            'final_state': {
                'reserve0_attos': self.serialize_attos_debug(reserve0),
                'reserve1_attos': self.serialize_attos_debug(reserve1),
                'total_supply_attos': self.serialize_attos_debug(total_supply),
                'k_last': self.serialize_attos_debug(k_last),
            },
        }
