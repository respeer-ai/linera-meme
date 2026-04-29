from decimal import Decimal


class PositionMetricsSwapHistoryExactnessSolver:
    def __init__(
        self,
        *,
        to_decimal,
        history_liquidity,
        reconstruct_pool_history,
        history_liquidity_before,
        split_protocol_fee_redeemable_attos,
        from_attos,
        effective_total_supply_attos_from_state,
        attos_within_tolerance,
        simulate_fee_free_from_open_state,
        normalize_non_negative,
        serialize_decimal,
        to_attos,
        epsilon,
    ):
        self.to_decimal = to_decimal
        self.history_liquidity = history_liquidity
        self.reconstruct_pool_history = reconstruct_pool_history
        self.history_liquidity_before = history_liquidity_before
        self.split_protocol_fee_redeemable_attos = split_protocol_fee_redeemable_attos
        self.from_attos = from_attos
        self.effective_total_supply_attos_from_state = effective_total_supply_attos_from_state
        self.attos_within_tolerance = attos_within_tolerance
        self.simulate_fee_free_from_open_state = simulate_fee_free_from_open_state
        self.normalize_non_negative = normalize_non_negative
        self.serialize_decimal = serialize_decimal
        self.to_attos = to_attos
        self.epsilon = epsilon

    def solve(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict],
        pool_transaction_history: list[dict] | None,
        owner_is_fee_to: bool,
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

        effective_history, states, blockers = self.reconstruct_pool_history(
            pool_transaction_history or [],
            virtual_initial_liquidity=bool(partial_metrics.get('virtual_initial_liquidity')),
        )
        if blockers:
            return None, blockers

        latest_position_tx = max(
            liquidity_history,
            key=lambda row: (int(row.get('created_at') or 0), int(row.get('transaction_id') or 0)),
        )
        opening_index = None
        for index, state in enumerate(states or []):
            if (
                state['transaction_id'] == latest_position_tx.get('transaction_id')
                and state['created_at'] == latest_position_tx.get('created_at')
            ):
                opening_index = index
                break
        if opening_index is None:
            return None, ['position_open_transaction_missing_from_pool_history']

        fee_to_opening_mint_case = False
        liquidity_basis = live_liquidity
        protocol_fee_amount0 = Decimal('0')
        protocol_fee_amount1 = Decimal('0')
        if live_liquidity is not None and live_liquidity - history_liquidity > self.epsilon:
            prior_history_liquidity = self.history_liquidity_before(liquidity_history, latest_position_tx)
            fee_to_opening_mint_case = (
                owner_is_fee_to
                and latest_position_tx.get('transaction_type') == 'AddLiquidity'
                and abs(prior_history_liquidity) <= self.epsilon
            )
            if not fee_to_opening_mint_case:
                return None, ['liquidity_history_mismatch']
            liquidity_basis = history_liquidity
            protocol_fee_amount0_attos, protocol_fee_amount1_attos = self.split_protocol_fee_redeemable_attos(
                redeemable_amount0=redeemable_amount0,
                redeemable_amount1=redeemable_amount1,
                live_liquidity=live_liquidity,
                history_liquidity=history_liquidity,
            )
            protocol_fee_amount0 = self.from_attos(protocol_fee_amount0_attos) or Decimal('0')
            protocol_fee_amount1 = self.from_attos(protocol_fee_amount1_attos) or Decimal('0')

        if latest_position_tx.get('transaction_type') != 'RemoveLiquidity':
            for tx in (effective_history or [])[:opening_index]:
                if tx.get('transaction_type') in {'BuyToken0', 'SellToken0'}:
                    if not fee_to_opening_mint_case:
                        return None, ['pool_has_swaps_before_latest_position_liquidity_change']
                    break

        current_total_supply_attos = self.to_attos(partial_metrics['total_supply_live'])
        liquidity_basis_attos = self.to_attos(liquidity_basis)
        if current_total_supply_attos is None or liquidity_basis_attos is None:
            return None, ['missing_live_liquidity_or_total_supply']
        if not self.attos_within_tolerance(
            self.effective_total_supply_attos_from_state(states[-1]),
            current_total_supply_attos,
        ):
            return None, ['pool_has_liquidity_changes_after_position_open']

        fee_free_state, blockers = self.simulate_fee_free_from_open_state(
            states,
            effective_history or [],
            opening_index,
        )
        if blockers:
            return None, blockers

        principal_amount0 = self.from_attos(
            liquidity_basis_attos * fee_free_state['reserve0'] // current_total_supply_attos
        )
        principal_amount1 = self.from_attos(
            liquidity_basis_attos * fee_free_state['reserve1'] // current_total_supply_attos
        )
        fee_amount0 = self.normalize_non_negative(
            redeemable_amount0 - protocol_fee_amount0 - principal_amount0
        )
        fee_amount1 = self.normalize_non_negative(
            redeemable_amount1 - protocol_fee_amount1 - principal_amount1
        )

        if fee_amount0 < 0 or fee_amount1 < 0:
            return None, ['fee_simulation_exceeds_live_redeemable']

        partial_metrics['metrics_status'] = 'exact_swap_history_no_post_open_liquidity_changes'
        partial_metrics['exact_fee_supported'] = True
        partial_metrics['exact_principal_supported'] = True
        partial_metrics['principal_amount0'] = self.serialize_decimal(principal_amount0)
        partial_metrics['principal_amount1'] = self.serialize_decimal(principal_amount1)
        partial_metrics['fee_amount0'] = self.serialize_decimal(fee_amount0)
        partial_metrics['fee_amount1'] = self.serialize_decimal(fee_amount1)
        partial_metrics['protocol_fee_amount0'] = self.serialize_decimal(protocol_fee_amount0)
        partial_metrics['protocol_fee_amount1'] = self.serialize_decimal(protocol_fee_amount1)
        partial_metrics['computation_blockers'] = []
        return partial_metrics, []
