class PositionMetricsSwapHistoryAlignmentChecker:
    def __init__(
        self,
        *,
        replay_entrypoint,
        fee_to_opening_mint_resolver,
        attos_within_tolerance,
        to_attos,
    ):
        self.replay_entrypoint = replay_entrypoint
        self.fee_to_opening_mint_resolver = fee_to_opening_mint_resolver
        self.attos_within_tolerance = attos_within_tolerance
        self.to_attos = to_attos

    def check(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict],
        pool_transaction_history: list[dict] | None,
        owner_is_fee_to: bool,
        precheck_context: dict,
    ) -> tuple[dict | None, list[str]]:
        effective_history, states, blockers = self.replay_entrypoint.reconstruct_pool_history(
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

        fee_to_context, blockers = self.fee_to_opening_mint_resolver.resolve(
            liquidity_history=liquidity_history,
            latest_position_tx=latest_position_tx,
            owner_is_fee_to=owner_is_fee_to,
            precheck_context=precheck_context,
        )
        if blockers:
            return None, blockers

        if latest_position_tx.get('transaction_type') != 'RemoveLiquidity':
            for tx in (effective_history or [])[:opening_index]:
                if tx.get('transaction_type') in {'BuyToken0', 'SellToken0'}:
                    if not fee_to_context['fee_to_opening_mint_case']:
                        return None, ['pool_has_swaps_before_latest_position_liquidity_change']
                    break

        current_total_supply_attos = self.to_attos(partial_metrics['total_supply_live'])
        liquidity_basis_attos = self.to_attos(fee_to_context['liquidity_basis'])
        if current_total_supply_attos is None or liquidity_basis_attos is None:
            return None, ['missing_live_liquidity_or_total_supply']
        if not self.attos_within_tolerance(
            self.replay_entrypoint.effective_total_supply_attos_from_state(states[-1]),
            current_total_supply_attos,
        ):
            return None, ['pool_has_liquidity_changes_after_position_open']

        fee_free_state, blockers = self.replay_entrypoint.simulate_fee_free_from_open_state(
            states,
            effective_history or [],
            opening_index,
        )
        if blockers:
            return None, blockers

        return {
            'current_total_supply_attos': current_total_supply_attos,
            'liquidity_basis_attos': liquidity_basis_attos,
            'fee_free_state': fee_free_state,
            'protocol_fee_amount0': fee_to_context['protocol_fee_amount0'],
            'protocol_fee_amount1': fee_to_context['protocol_fee_amount1'],
            **precheck_context,
        }, []
