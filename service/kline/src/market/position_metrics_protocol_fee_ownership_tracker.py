class PositionMetricsProtocolFeeOwnershipTracker:
    def __init__(self, *, serialize_attos):
        self.serialize_attos = serialize_attos

    def summarize(
        self,
        *,
        owner: str,
        effective_history: list[dict[str, object]],
        states: list[dict[str, object]],
        latest_position_tx: dict[str, object],
        fee_to_history: list[dict[str, object]] | None,
    ) -> dict[str, object] | None:
        basis_index = self._basis_index(
            effective_history=effective_history,
            latest_position_tx=latest_position_tx,
        )
        if basis_index is None:
            return None
        ordered_fee_to_history = sorted(
            fee_to_history or [],
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
                str(row.get('fee_to_account') or ''),
            ),
        )
        fee_to_cursor = -1
        saw_add_after_basis = False
        basis_owned_by_current_owner_attos = 0
        post_basis_owned_by_current_owner_attos = 0
        post_basis_owned_by_current_owner_before_first_add_attos = 0
        owned_by_other_accounts_attos = 0
        owner_unknown_attos = 0

        for index in range(basis_index, len(effective_history)):
            row = effective_history[index]
            state = states[index]
            protocol_fee_minted_attos = int(state.get('protocol_fee_minted_after') or 0)
            row_key = (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
            )
            fee_to_cursor = self._advance_fee_to_cursor(
                ordered_fee_to_history=ordered_fee_to_history,
                fee_to_cursor=fee_to_cursor,
                row_key=row_key,
            )
            fee_to_account = None
            if fee_to_cursor >= 0:
                fee_to_account = ordered_fee_to_history[fee_to_cursor].get('fee_to_account')
            if protocol_fee_minted_attos > 0:
                if fee_to_account is None:
                    owner_unknown_attos += protocol_fee_minted_attos
                elif str(fee_to_account) == owner:
                    if index == basis_index:
                        basis_owned_by_current_owner_attos += protocol_fee_minted_attos
                    else:
                        post_basis_owned_by_current_owner_attos += protocol_fee_minted_attos
                        if not saw_add_after_basis:
                            post_basis_owned_by_current_owner_before_first_add_attos += protocol_fee_minted_attos
                else:
                    owned_by_other_accounts_attos += protocol_fee_minted_attos
            if index > basis_index and row.get('transaction_type') == 'AddLiquidity':
                saw_add_after_basis = True

        owned_by_current_owner_current_attos = (
            basis_owned_by_current_owner_attos + post_basis_owned_by_current_owner_attos
        )
        return {
            'basis_protocol_fee_liquidity_owned_by_current_owner': self.serialize_attos(
                basis_owned_by_current_owner_attos
            ),
            'post_basis_protocol_fee_liquidity_owned_by_current_owner': self.serialize_attos(
                post_basis_owned_by_current_owner_attos
            ),
            'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': self.serialize_attos(
                post_basis_owned_by_current_owner_before_first_add_attos
            ),
            'protocol_fee_liquidity_owned_by_current_owner_current': self.serialize_attos(
                owned_by_current_owner_current_attos
            ),
            'protocol_fee_liquidity_owned_by_other_accounts': self.serialize_attos(
                owned_by_other_accounts_attos
            ),
            'protocol_fee_liquidity_owner_unknown': self.serialize_attos(owner_unknown_attos),
            'protocol_fee_current_owner_provenance_case': self._provenance_case(
                owned_by_current_owner_current_attos=owned_by_current_owner_current_attos,
                owned_by_other_accounts_attos=owned_by_other_accounts_attos,
                owner_unknown_attos=owner_unknown_attos,
            ),
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

    def _advance_fee_to_cursor(
        self,
        *,
        ordered_fee_to_history: list[dict[str, object]],
        fee_to_cursor: int,
        row_key: tuple[int, int],
    ) -> int:
        while fee_to_cursor + 1 < len(ordered_fee_to_history):
            candidate = ordered_fee_to_history[fee_to_cursor + 1]
            candidate_key = (
                int(candidate.get('created_at') or 0),
                int(candidate.get('transaction_id') or 0),
            )
            if candidate_key > row_key:
                break
            fee_to_cursor += 1
        return fee_to_cursor

    def _provenance_case(
        self,
        *,
        owned_by_current_owner_current_attos: int,
        owned_by_other_accounts_attos: int,
        owner_unknown_attos: int,
    ) -> str:
        if (
            owned_by_current_owner_current_attos == 0
            and owned_by_other_accounts_attos == 0
            and owner_unknown_attos == 0
        ):
            return 'no_protocol_fee_mints'
        if (
            owned_by_current_owner_current_attos > 0
            and owned_by_other_accounts_attos == 0
            and owner_unknown_attos == 0
        ):
            return 'all_mints_owned_by_current_owner'
        if (
            owned_by_current_owner_current_attos == 0
            and owned_by_other_accounts_attos > 0
            and owner_unknown_attos == 0
        ):
            return 'no_mints_owned_by_current_owner'
        if (
            owned_by_current_owner_current_attos == 0
            and owned_by_other_accounts_attos == 0
            and owner_unknown_attos > 0
        ):
            return 'unknown_owner_mints_only'
        if (
            owned_by_current_owner_current_attos > 0
            and owned_by_other_accounts_attos > 0
            and owner_unknown_attos == 0
        ):
            return 'owner_and_non_owner_mints'
        if (
            owned_by_current_owner_current_attos > 0
            and owned_by_other_accounts_attos == 0
            and owner_unknown_attos > 0
        ):
            return 'owner_and_unknown_owner_mints'
        if (
            owned_by_current_owner_current_attos == 0
            and owned_by_other_accounts_attos > 0
            and owner_unknown_attos > 0
        ):
            return 'non_owner_and_unknown_owner_mints'
        return 'owner_non_owner_and_unknown_owner_mints'
