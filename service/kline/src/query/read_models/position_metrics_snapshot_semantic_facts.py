class PositionMetricsSnapshotSemanticFacts:
    def __init__(self, payload: dict | None):
        self.payload = payload if isinstance(payload, dict) else None

    @classmethod
    def from_state_payload(cls, payload: object):
        payload_dict = payload if isinstance(payload, dict) else {}
        exact_current_principal = cls._dict_field(payload_dict, 'exact_current_principal')
        fee_to_continuity = cls._dict_field(payload_dict, 'fee_to_continuity')
        return cls(
            {
                'prior_liquidity_before_basis': payload_dict.get('prior_liquidity_before_basis'),
                'has_only_zero_liquidity_before_basis': payload_dict.get('has_only_zero_liquidity_before_basis'),
                'basis_opens_current_round': payload_dict.get('basis_opens_current_round'),
                'current_round_liquidity_event_count': payload_dict.get('current_round_liquidity_event_count'),
                'current_round_started_at': payload_dict.get('current_round_started_at'),
                'current_round_started_transaction_id': payload_dict.get('current_round_started_transaction_id'),
                'current_round_trade_count_before_basis': payload_dict.get('current_round_trade_count_before_basis'),
                'trade_count_between_basis_and_fee_free_basis': payload_dict.get(
                    'trade_count_between_basis_and_fee_free_basis'
                ),
                'exact_current_principal_case': exact_current_principal.get('exact_current_principal_case'),
                'principal_amount_0_current': exact_current_principal.get('principal_amount_0_current'),
                'principal_amount_1_current': exact_current_principal.get('principal_amount_1_current'),
                'post_basis_remove_count': exact_current_principal.get('post_basis_remove_count'),
                'basis_protocol_fee_liquidity_minted': exact_current_principal.get(
                    'basis_protocol_fee_liquidity_minted'
                ),
                'post_basis_protocol_fee_liquidity_minted': exact_current_principal.get(
                    'post_basis_protocol_fee_liquidity_minted'
                ),
                'post_basis_protocol_fee_mint_event_count': exact_current_principal.get(
                    'post_basis_protocol_fee_mint_event_count'
                ),
                'post_basis_protocol_fee_liquidity_minted_before_first_add': exact_current_principal.get(
                    'post_basis_protocol_fee_liquidity_minted_before_first_add'
                ),
                'fee_to_continuous_protocol_fee_liquidity_current': exact_current_principal.get(
                    'fee_to_continuous_protocol_fee_liquidity_current'
                ),
                'protocol_fee_liquidity_provenance_case': exact_current_principal.get(
                    'protocol_fee_liquidity_provenance_case'
                ),
                'protocol_fee_current_owner_provenance_case': exact_current_principal.get(
                    'protocol_fee_current_owner_provenance_case'
                ),
                'basis_protocol_fee_liquidity_owned_by_current_owner': exact_current_principal.get(
                    'basis_protocol_fee_liquidity_owned_by_current_owner'
                ),
                'post_basis_protocol_fee_liquidity_owned_by_current_owner': exact_current_principal.get(
                    'post_basis_protocol_fee_liquidity_owned_by_current_owner'
                ),
                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': exact_current_principal.get(
                    'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add'
                ),
                'protocol_fee_liquidity_owned_by_current_owner_current': exact_current_principal.get(
                    'protocol_fee_liquidity_owned_by_current_owner_current'
                ),
                'protocol_fee_liquidity_owned_by_other_accounts': exact_current_principal.get(
                    'protocol_fee_liquidity_owned_by_other_accounts'
                ),
                'protocol_fee_liquidity_owner_unknown': exact_current_principal.get(
                    'protocol_fee_liquidity_owner_unknown'
                ),
                'fee_to_continuity_case': fee_to_continuity.get('continuity_case'),
                'fee_to_continuity_change_count_after_basis': fee_to_continuity.get('change_count_after_basis'),
                'fee_to_continuity_known_before_basis': fee_to_continuity.get('known_before_basis'),
                'fee_to_continuity_owner': fee_to_continuity.get('owner'),
                'fee_to_account_at_basis': fee_to_continuity.get('fee_to_account_at_basis'),
                'fee_to_account_latest_known': fee_to_continuity.get('fee_to_account_latest_known'),
                'trailing_24h_fee_amount_0': exact_current_principal.get('trailing_24h_fee_amount_0'),
                'trailing_24h_fee_amount_1': exact_current_principal.get('trailing_24h_fee_amount_1'),
                'trailing_24h_fee_window_start_ms': exact_current_principal.get('trailing_24h_fee_window_start_ms'),
                'trailing_24h_fee_window_end_ms': exact_current_principal.get('trailing_24h_fee_window_end_ms'),
            }
        )

    def raw(self) -> dict:
        if self.payload is None:
            return {}
        return self.payload

    def get(self, field_name: str) -> object:
        if self.payload is None:
            return None
        return self.payload.get(field_name)

    def has(self, field_name: str) -> bool:
        if self.payload is None:
            return False
        return field_name in self.payload

    def fee_to_continuity_case(self) -> str | None:
        value = self.get('fee_to_continuity_case')
        if value in (None, ''):
            return None
        return str(value)

    def fee_to_continuity_change_count_after_basis(self) -> int | None:
        value = self.get('fee_to_continuity_change_count_after_basis')
        if value in (None, ''):
            return None
        return int(value)

    def fee_to_continuity_known_before_basis(self) -> bool | None:
        if not self.has('fee_to_continuity_known_before_basis'):
            return None
        value = self.get('fee_to_continuity_known_before_basis')
        if value in (None, ''):
            return None
        return bool(value)

    def fee_to_continuity_owner(self) -> str | None:
        value = self.get('fee_to_continuity_owner')
        if value in (None, ''):
            return None
        return str(value)

    def fee_to_account_at_basis(self) -> str | None:
        value = self.get('fee_to_account_at_basis')
        if value in (None, ''):
            return None
        return str(value)

    def fee_to_account_latest_known(self) -> str | None:
        value = self.get('fee_to_account_latest_known')
        if value in (None, ''):
            return None
        return str(value)

    def trailing_24h_fee_amount_0(self) -> str | None:
        value = self.get('trailing_24h_fee_amount_0')
        if value in (None, ''):
            return None
        return str(value)

    def trailing_24h_fee_amount_1(self) -> str | None:
        value = self.get('trailing_24h_fee_amount_1')
        if value in (None, ''):
            return None
        return str(value)

    def trailing_24h_fee_window_start_ms(self) -> int | None:
        value = self.get('trailing_24h_fee_window_start_ms')
        if value in (None, ''):
            return None
        return int(value)

    def trailing_24h_fee_window_end_ms(self) -> int | None:
        value = self.get('trailing_24h_fee_window_end_ms')
        if value in (None, ''):
            return None
        return int(value)

    def basis_opens_current_round(self) -> bool:
        return bool(self.get('basis_opens_current_round'))

    def has_only_zero_liquidity_before_basis(self) -> bool:
        return bool(self.get('has_only_zero_liquidity_before_basis'))

    def current_round_liquidity_event_count(self) -> int | None:
        value = self.get('current_round_liquidity_event_count')
        if value in (None, ''):
            return None
        return int(value)

    def current_round_started_at(self) -> int | None:
        value = self.get('current_round_started_at')
        if value in (None, ''):
            return None
        return int(value)

    def current_round_started_transaction_id(self) -> int | None:
        value = self.get('current_round_started_transaction_id')
        if value in (None, ''):
            return None
        return int(value)

    def current_round_trade_count_before_basis(self) -> int | None:
        value = self.get('current_round_trade_count_before_basis')
        if value in (None, ''):
            return None
        return int(value)

    def trade_count_between_basis_and_fee_free_basis(self) -> int | None:
        value = self.get('trade_count_between_basis_and_fee_free_basis')
        if value in (None, ''):
            return None
        return int(value)

    def exact_current_principal_case(self) -> str | None:
        value = self.get('exact_current_principal_case')
        if value in (None, ''):
            return None
        return str(value)

    def principal_amount_0_current(self) -> str | None:
        value = self.get('principal_amount_0_current')
        if value in (None, ''):
            return None
        return str(value)

    def principal_amount_1_current(self) -> str | None:
        value = self.get('principal_amount_1_current')
        if value in (None, ''):
            return None
        return str(value)

    def post_basis_remove_count(self) -> int:
        value = self.get('post_basis_remove_count')
        if value in (None, ''):
            return 0
        return int(value)

    def protocol_fee_liquidity_provenance_case(self) -> str | None:
        value = self.get('protocol_fee_liquidity_provenance_case')
        if value in (None, ''):
            return None
        return str(value)

    def protocol_fee_current_owner_provenance_case(self) -> str | None:
        value = self.get('protocol_fee_current_owner_provenance_case')
        if value in (None, ''):
            return None
        return str(value)

    def basis_protocol_fee_liquidity_minted(self) -> str | None:
        value = self.get('basis_protocol_fee_liquidity_minted')
        if value in (None, ''):
            return None
        return str(value)

    def post_basis_protocol_fee_liquidity_minted(self) -> str | None:
        value = self.get('post_basis_protocol_fee_liquidity_minted')
        if value in (None, ''):
            return None
        return str(value)

    def post_basis_protocol_fee_mint_event_count(self) -> int | None:
        value = self.get('post_basis_protocol_fee_mint_event_count')
        if value in (None, ''):
            return None
        return int(value)

    def post_basis_protocol_fee_liquidity_minted_before_first_add(self) -> str | None:
        value = self.get('post_basis_protocol_fee_liquidity_minted_before_first_add')
        if value in (None, ''):
            return None
        return str(value)

    def fee_to_continuous_protocol_fee_liquidity_current(self) -> str | None:
        value = self.get('fee_to_continuous_protocol_fee_liquidity_current')
        if value in (None, ''):
            return None
        return str(value)

    def basis_protocol_fee_liquidity_owned_by_current_owner(self) -> str | None:
        value = self.get('basis_protocol_fee_liquidity_owned_by_current_owner')
        if value in (None, ''):
            return None
        return str(value)

    def post_basis_protocol_fee_liquidity_owned_by_current_owner(self) -> str | None:
        value = self.get('post_basis_protocol_fee_liquidity_owned_by_current_owner')
        if value in (None, ''):
            return None
        return str(value)

    def post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add(self) -> str | None:
        value = self.get('post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add')
        if value in (None, ''):
            return None
        return str(value)

    def protocol_fee_liquidity_owned_by_current_owner_current(self) -> str | None:
        value = self.get('protocol_fee_liquidity_owned_by_current_owner_current')
        if value in (None, ''):
            return None
        return str(value)

    def protocol_fee_liquidity_owned_by_other_accounts(self) -> str | None:
        value = self.get('protocol_fee_liquidity_owned_by_other_accounts')
        if value in (None, ''):
            return None
        return str(value)

    def protocol_fee_liquidity_owner_unknown(self) -> str | None:
        value = self.get('protocol_fee_liquidity_owner_unknown')
        if value in (None, ''):
            return None
        return str(value)

    @classmethod
    def _dict_field(cls, payload: dict, field_name: str) -> dict:
        value = payload.get(field_name)
        if isinstance(value, dict):
            return value
        return {}
