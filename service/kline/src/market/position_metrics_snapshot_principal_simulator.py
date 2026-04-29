class PositionMetricsSnapshotPrincipalSimulator:
    def __init__(
        self,
        *,
        to_attos,
        from_attos,
        serialize_attos,
        swap_expected_out_attos,
        effective_total_supply_attos,
    ):
        self.to_attos = to_attos
        self.from_attos = from_attos
        self.serialize_attos = serialize_attos
        self.swap_expected_out_attos = swap_expected_out_attos
        self.effective_total_supply_attos = effective_total_supply_attos

    def simulate_current_principal(
        self,
        *,
        effective_history: list[dict[str, object]],
        states: list[dict[str, object]],
        latest_position_tx: dict[str, object],
        tracked_liquidity_attos: int,
        basis_type: str,
        basis_opens_current_round: bool,
        current_round_trade_count_before_basis: int,
    ) -> dict[str, object] | None:
        basis_index = self._basis_index(
            effective_history=effective_history,
            latest_position_tx=latest_position_tx,
        )
        if basis_index is None:
            return None
        if (
            basis_type == 'add_liquidity'
            and not basis_opens_current_round
            and current_round_trade_count_before_basis > 0
        ):
            return None
        if tracked_liquidity_attos <= 0:
            return {
                'principal_amount_0_current': '0',
                'principal_amount_1_current': '0',
                'exact_current_principal_case': 'zero_liquidity',
            }

        basis_state = states[basis_index]
        reserve0 = int(basis_state.get('reserve0_after') or 0)
        reserve1 = int(basis_state.get('reserve1_after') or 0)
        total_supply = self.effective_total_supply_attos(basis_state)
        basis_protocol_fee_liquidity_minted_attos = int(basis_state.get('protocol_fee_minted_after') or 0)
        if reserve0 <= 0 or reserve1 <= 0 or total_supply <= 0:
            return None

        saw_add_after_basis = False
        saw_swap_before_first_add_after_basis = False
        saw_remove_after_basis = False
        post_basis_add_count = 0
        post_basis_remove_count = 0
        post_basis_swap_count = 0
        post_basis_protocol_fee_liquidity_minted_attos = 0
        post_basis_protocol_fee_mint_event_count = 0
        post_basis_protocol_fee_liquidity_minted_before_first_add_attos = 0

        for row, state in zip(effective_history[basis_index + 1:], states[basis_index + 1:]):
            transaction_type = row.get('transaction_type')
            protocol_fee_minted_attos = int(state.get('protocol_fee_minted_after') or 0)
            if protocol_fee_minted_attos > 0:
                post_basis_protocol_fee_liquidity_minted_attos += protocol_fee_minted_attos
                post_basis_protocol_fee_mint_event_count += 1
                if not saw_add_after_basis:
                    post_basis_protocol_fee_liquidity_minted_before_first_add_attos += protocol_fee_minted_attos
            if transaction_type == 'BuyToken0':
                amount1_in = self.to_attos(row.get('amount_1_in')) or 0
                amount0_out = self.swap_expected_out_attos(
                    'BuyToken0',
                    reserve0,
                    reserve1,
                    0,
                    amount1_in,
                )
                if amount1_in <= 0 or amount0_out is None or amount0_out <= 0 or amount0_out >= reserve0:
                    return None
                reserve1 += amount1_in
                reserve0 -= amount0_out
                post_basis_swap_count += 1
                if not saw_add_after_basis:
                    saw_swap_before_first_add_after_basis = True
            elif transaction_type == 'SellToken0':
                amount0_in = self.to_attos(row.get('amount_0_in')) or 0
                amount1_out = self.swap_expected_out_attos(
                    'SellToken0',
                    reserve0,
                    reserve1,
                    amount0_in,
                    0,
                )
                if amount0_in <= 0 or amount1_out is None or amount1_out <= 0 or amount1_out >= reserve1:
                    return None
                reserve0 += amount0_in
                reserve1 -= amount1_out
                post_basis_swap_count += 1
                if not saw_add_after_basis:
                    saw_swap_before_first_add_after_basis = True
            elif transaction_type == 'AddLiquidity':
                amount0_in = self.to_attos(row.get('amount_0_in')) or 0
                amount1_in = self.to_attos(row.get('amount_1_in')) or 0
                if amount0_in <= 0 or amount1_in <= 0:
                    return None
                minted_liquidity = min(
                    amount0_in * total_supply // reserve0,
                    amount1_in * total_supply // reserve1,
                )
                if minted_liquidity <= 0:
                    return None
                reserve0 += amount0_in
                reserve1 += amount1_in
                total_supply += minted_liquidity
                saw_add_after_basis = True
                post_basis_add_count += 1
            elif transaction_type == 'RemoveLiquidity':
                liquidity = self.to_attos(row.get('liquidity')) or 0
                if liquidity <= 0 or liquidity > total_supply:
                    return None
                amount0_out = liquidity * reserve0 // total_supply
                amount1_out = liquidity * reserve1 // total_supply
                if amount0_out <= 0 or amount1_out <= 0 or amount0_out >= reserve0 or amount1_out >= reserve1:
                    return None
                reserve0 -= amount0_out
                reserve1 -= amount1_out
                total_supply -= liquidity
                saw_remove_after_basis = True
                post_basis_remove_count += 1
            else:
                return None

        principal_amount0_attos = tracked_liquidity_attos * reserve0 // total_supply
        principal_amount1_attos = tracked_liquidity_attos * reserve1 // total_supply
        fee_to_continuous_protocol_fee_liquidity_current_attos = (
            basis_protocol_fee_liquidity_minted_attos + post_basis_protocol_fee_liquidity_minted_attos
        )
        if (saw_add_after_basis or saw_remove_after_basis) and saw_swap_before_first_add_after_basis:
            exact_case = 'post_basis_liquidity_changes_with_intervening_swaps'
        elif saw_add_after_basis or saw_remove_after_basis:
            exact_case = 'post_basis_liquidity_changes_without_intervening_swaps'
        else:
            exact_case = 'post_basis_swaps_without_liquidity_changes'
        if (
            basis_protocol_fee_liquidity_minted_attos > 0
            and post_basis_protocol_fee_liquidity_minted_attos > 0
        ):
            protocol_fee_liquidity_provenance_case = 'basis_and_post_basis_mints'
        elif basis_protocol_fee_liquidity_minted_attos > 0:
            protocol_fee_liquidity_provenance_case = 'basis_only_mints'
        elif post_basis_protocol_fee_liquidity_minted_attos > 0:
            protocol_fee_liquidity_provenance_case = 'post_basis_only_mints'
        else:
            protocol_fee_liquidity_provenance_case = 'no_protocol_fee_mints'
        return {
            'principal_amount_0_current': self.serialize_attos(principal_amount0_attos),
            'principal_amount_1_current': self.serialize_attos(principal_amount1_attos),
            'exact_current_principal_case': exact_case,
            'post_basis_add_count': post_basis_add_count,
            'post_basis_remove_count': post_basis_remove_count,
            'post_basis_swap_count': post_basis_swap_count,
            'basis_protocol_fee_liquidity_minted': self.serialize_attos(basis_protocol_fee_liquidity_minted_attos),
            'post_basis_protocol_fee_liquidity_minted': self.serialize_attos(
                post_basis_protocol_fee_liquidity_minted_attos
            ),
            'post_basis_protocol_fee_mint_event_count': post_basis_protocol_fee_mint_event_count,
            'post_basis_protocol_fee_liquidity_minted_before_first_add': self.serialize_attos(
                post_basis_protocol_fee_liquidity_minted_before_first_add_attos
            ),
            'fee_to_continuous_protocol_fee_liquidity_current': self.serialize_attos(
                fee_to_continuous_protocol_fee_liquidity_current_attos
            ),
            'protocol_fee_liquidity_provenance_case': protocol_fee_liquidity_provenance_case,
        }

    def _basis_index(
        self,
        *,
        effective_history: list[dict[str, object]],
        latest_position_tx: dict[str, object],
    ) -> int | None:
        latest_key = (
            int(latest_position_tx.get('created_at') or 0),
            int(latest_position_tx.get('transaction_id') or 0),
            str(latest_position_tx.get('transaction_type') or ''),
        )
        for index, row in enumerate(effective_history):
            row_key = (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
                str(row.get('transaction_type') or ''),
            )
            if row_key == latest_key:
                return index
        return None
