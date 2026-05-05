from query.read_models.position_metrics_snapshot_semantic_facts import PositionMetricsSnapshotSemanticFacts


class PositionMetricsPositionBasisSnapshot:
    def __init__(self, payload: dict | None):
        self.payload = payload

    def raw(self) -> dict | None:
        return self.payload

    def semantic_facts(self) -> PositionMetricsSnapshotSemanticFacts:
        if self.payload is None:
            return PositionMetricsSnapshotSemanticFacts(None)
        return PositionMetricsSnapshotSemanticFacts(self.payload.get('semantic_facts'))

    def status(self):
        if self.payload is None:
            return None
        return self.payload.get('status')

    def basis_type(self):
        if self.payload is None:
            return None
        return self.payload.get('basis_type')

    def current_liquidity(self):
        if self.payload is None:
            return None
        return self.payload.get('current_liquidity')

    def basis_transaction_id(self):
        if self.payload is None:
            return None
        return self.payload.get('basis_transaction_id')

    def basis_time_ms(self):
        if self.payload is None:
            return None
        return self.payload.get('basis_time_ms')

    def prior_liquidity_before_basis(self):
        return self.semantic_facts().get('prior_liquidity_before_basis')

    def post_basis_remove_count(self):
        return self.semantic_facts().post_basis_remove_count()

    def has_only_zero_liquidity_before_basis(self):
        return self.semantic_facts().has_only_zero_liquidity_before_basis()

    def basis_opens_current_round(self):
        return self.semantic_facts().basis_opens_current_round()

    def current_round_liquidity_event_count(self):
        return self.semantic_facts().current_round_liquidity_event_count()

    def current_round_started_at(self):
        return self.semantic_facts().current_round_started_at()

    def current_round_started_transaction_id(self):
        return self.semantic_facts().current_round_started_transaction_id()

    def current_round_trade_count_before_basis(self):
        return self.semantic_facts().current_round_trade_count_before_basis()

    def trade_count_between_basis_and_fee_free_basis(self):
        return self.semantic_facts().trade_count_between_basis_and_fee_free_basis()

    def exact_current_principal_case(self):
        return self.semantic_facts().exact_current_principal_case()

    def principal_amount_0_current(self):
        return self.semantic_facts().principal_amount_0_current()

    def principal_amount_1_current(self):
        return self.semantic_facts().principal_amount_1_current()

    def post_basis_protocol_fee_mint_event_count(self):
        return self.semantic_facts().post_basis_protocol_fee_mint_event_count()

    def protocol_fee_liquidity_provenance_case(self):
        return self.semantic_facts().protocol_fee_liquidity_provenance_case()

    def protocol_fee_current_owner_provenance_case(self):
        return self.semantic_facts().protocol_fee_current_owner_provenance_case()

    def fee_to_continuity_case(self):
        return self.semantic_facts().fee_to_continuity_case()

    def fee_to_continuity_owner(self):
        return self.semantic_facts().fee_to_continuity_owner()

    def fee_to_continuity_known_before_basis(self):
        return self.semantic_facts().fee_to_continuity_known_before_basis()

    def fee_to_account_at_basis(self):
        return self.semantic_facts().fee_to_account_at_basis()

    def fee_to_account_latest_known(self):
        return self.semantic_facts().fee_to_account_latest_known()

    def basis_protocol_fee_liquidity_minted(self):
        return self.semantic_facts().basis_protocol_fee_liquidity_minted()

    def post_basis_protocol_fee_liquidity_minted(self):
        return self.semantic_facts().post_basis_protocol_fee_liquidity_minted()

    def post_basis_protocol_fee_liquidity_minted_before_first_add(self):
        return self.semantic_facts().post_basis_protocol_fee_liquidity_minted_before_first_add()

    def fee_to_continuous_protocol_fee_liquidity_current(self):
        return self.semantic_facts().fee_to_continuous_protocol_fee_liquidity_current()

    def basis_protocol_fee_liquidity_owned_by_current_owner(self):
        return self.semantic_facts().basis_protocol_fee_liquidity_owned_by_current_owner()

    def post_basis_protocol_fee_liquidity_owned_by_current_owner(self):
        return self.semantic_facts().post_basis_protocol_fee_liquidity_owned_by_current_owner()

    def post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add(self):
        return self.semantic_facts().post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add()

    def protocol_fee_liquidity_owned_by_current_owner_current(self):
        return self.semantic_facts().protocol_fee_liquidity_owned_by_current_owner_current()

    def protocol_fee_liquidity_owned_by_other_accounts(self):
        return self.semantic_facts().protocol_fee_liquidity_owned_by_other_accounts()

    def protocol_fee_liquidity_owner_unknown(self):
        return self.semantic_facts().protocol_fee_liquidity_owner_unknown()

    def summary_dict(self) -> dict | None:
        if self.payload is None:
            return None
        facts = self.semantic_facts()
        return {
            'status': self.status(),
            'basis_type': self.basis_type(),
            'current_liquidity': self.current_liquidity(),
            'basis_transaction_id': self._int_or_none(self.basis_transaction_id()),
            'basis_time_ms': self._int_or_none(self.basis_time_ms()),
            'basis_opens_current_round': facts.basis_opens_current_round(),
            'has_only_zero_liquidity_before_basis': facts.has_only_zero_liquidity_before_basis(),
            'current_round_liquidity_event_count': facts.current_round_liquidity_event_count(),
            'current_round_started_at': facts.current_round_started_at(),
            'current_round_started_transaction_id': facts.current_round_started_transaction_id(),
            'current_round_trade_count_before_basis': facts.current_round_trade_count_before_basis(),
            'trade_count_between_basis_and_fee_free_basis': facts.trade_count_between_basis_and_fee_free_basis(),
            'exact_current_principal_case': facts.exact_current_principal_case(),
            'protocol_fee_liquidity_provenance_case': facts.protocol_fee_liquidity_provenance_case(),
            'basis_protocol_fee_liquidity_minted': facts.basis_protocol_fee_liquidity_minted(),
            'post_basis_protocol_fee_liquidity_minted': facts.post_basis_protocol_fee_liquidity_minted(),
            'post_basis_protocol_fee_mint_event_count': facts.post_basis_protocol_fee_mint_event_count(),
            'post_basis_protocol_fee_liquidity_minted_before_first_add': (
                facts.post_basis_protocol_fee_liquidity_minted_before_first_add()
            ),
            'fee_to_continuous_protocol_fee_liquidity_current': (
                facts.fee_to_continuous_protocol_fee_liquidity_current()
            ),
            'protocol_fee_current_owner_provenance_case': facts.protocol_fee_current_owner_provenance_case(),
            'basis_protocol_fee_liquidity_owned_by_current_owner': (
                facts.basis_protocol_fee_liquidity_owned_by_current_owner()
            ),
            'post_basis_protocol_fee_liquidity_owned_by_current_owner': (
                facts.post_basis_protocol_fee_liquidity_owned_by_current_owner()
            ),
            'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': (
                facts.post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add()
            ),
            'protocol_fee_liquidity_owned_by_current_owner_current': (
                facts.protocol_fee_liquidity_owned_by_current_owner_current()
            ),
            'protocol_fee_liquidity_owned_by_other_accounts': (
                facts.protocol_fee_liquidity_owned_by_other_accounts()
            ),
            'protocol_fee_liquidity_owner_unknown': facts.protocol_fee_liquidity_owner_unknown(),
            'fee_to_continuity_case': facts.fee_to_continuity_case(),
            'fee_to_continuity_change_count_after_basis': facts.fee_to_continuity_change_count_after_basis(),
            'fee_to_continuity_known_before_basis': facts.fee_to_continuity_known_before_basis(),
            'fee_to_continuity_owner': facts.fee_to_continuity_owner(),
            'fee_to_account_at_basis': facts.fee_to_account_at_basis(),
            'fee_to_account_latest_known': facts.fee_to_account_latest_known(),
        }

    def shadow_latest_dict(self) -> dict:
        return {
            'latest_position_transaction_id': self._int_or_none(self.basis_transaction_id()),
            'latest_position_created_at': self._int_or_none(self.basis_time_ms()),
        }

    def _int_or_none(self, value: object) -> int | None:
        if value in (None, ''):
            return None
        return int(value)
