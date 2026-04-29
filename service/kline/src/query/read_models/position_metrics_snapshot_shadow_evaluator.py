from decimal import Decimal
from query.read_models.position_metrics_protocol_fee_split_semantics import PositionMetricsProtocolFeeSplitSemantics


class PositionMetricsSnapshotShadowEvaluator:
    def __init__(
        self,
        *,
        protocol_fee_split_semantics: PositionMetricsProtocolFeeSplitSemantics | None = None,
    ):
        self.protocol_fee_split_semantics = protocol_fee_split_semantics or PositionMetricsProtocolFeeSplitSemantics()

    def evaluate(
        self,
        *,
        position: dict,
        live_metrics: dict,
        liquidity_history: list[dict] | None,
        pool_transaction_history: list[dict] | None,
        position_basis_snapshot: dict | None,
        pool_state_snapshot: dict | None,
    ) -> dict:
        latest_position_tx = self._latest_row(liquidity_history)
        latest_pool_tx = self._latest_row(pool_transaction_history)
        latest_pool_trade_time_ms = self._latest_created_at(
            pool_transaction_history,
            {'BuyToken0', 'SellToken0'},
        )
        latest_pool_liquidity_time_ms = self._latest_created_at(
            pool_transaction_history,
            {'AddLiquidity', 'RemoveLiquidity'},
        )
        mismatch_codes = []

        if position_basis_snapshot is None:
            mismatch_codes.append('missing_position_basis_snapshot')
        if pool_state_snapshot is None:
            mismatch_codes.append('missing_pool_state_snapshot')

        if position_basis_snapshot is not None:
            if str(position_basis_snapshot.get('status') or '') != str(position.get('status') or ''):
                mismatch_codes.append('position_status_mismatch')
            if not self._decimal_equal(
                position_basis_snapshot.get('current_liquidity'),
                position.get('current_liquidity'),
            ):
                mismatch_codes.append('position_current_liquidity_mismatch')
            if latest_position_tx is not None:
                if self._int_or_none(position_basis_snapshot.get('basis_transaction_id')) != self._int_or_none(
                    latest_position_tx.get('transaction_id')
                ):
                    mismatch_codes.append('position_basis_transaction_id_mismatch')
                if self._int_or_none(position_basis_snapshot.get('basis_time_ms')) != self._int_or_none(
                    latest_position_tx.get('created_at')
                ):
                    mismatch_codes.append('position_basis_time_mismatch')

        if pool_state_snapshot is not None:
            if latest_pool_tx is not None:
                if self._int_or_none(pool_state_snapshot.get('last_transaction_id')) != self._int_or_none(
                    latest_pool_tx.get('transaction_id')
                ):
                    mismatch_codes.append('pool_last_transaction_id_mismatch')
            if self._int_or_none(pool_state_snapshot.get('last_trade_time_ms')) != latest_pool_trade_time_ms:
                mismatch_codes.append('pool_last_trade_time_mismatch')
            if self._int_or_none(pool_state_snapshot.get('last_liquidity_event_time_ms')) != latest_pool_liquidity_time_ms:
                mismatch_codes.append('pool_last_liquidity_event_time_mismatch')

        position_snapshot_summary = self._position_snapshot_summary(
            position_basis_snapshot,
            live_metrics=live_metrics,
        )
        pool_snapshot_summary = self._pool_snapshot_summary(pool_state_snapshot)
        comparable = position_basis_snapshot is not None and pool_state_snapshot is not None
        readiness, readiness_reason_codes = self._readiness(
            comparable=comparable,
            mismatch_codes=mismatch_codes,
            live_metrics=live_metrics,
            position_snapshot_summary=position_snapshot_summary,
        )
        return {
            'owner': position['owner'],
            'pool_application': position['pool_application'],
            'pool_id': position['pool_id'],
            'status': position.get('status') or 'active',
            'metrics_status': live_metrics.get('metrics_status'),
            'exact_fee_supported': bool(live_metrics.get('exact_fee_supported')),
            'exact_principal_supported': bool(live_metrics.get('exact_principal_supported')),
            'snapshot_shadow': {
                'comparable': comparable,
                'position_basis_snapshot_present': position_basis_snapshot is not None,
                'pool_state_snapshot_present': pool_state_snapshot is not None,
                'mismatch_codes': mismatch_codes,
                'readiness': readiness,
                'readiness_reason_codes': readiness_reason_codes,
                'live_position_status': position.get('status') or 'active',
                'live_current_liquidity': position.get('current_liquidity'),
                'live_metrics_status': live_metrics.get('metrics_status'),
                'computation_blockers': list(live_metrics.get('computation_blockers') or []),
                'value_warning_codes': list(live_metrics.get('value_warning_codes') or []),
                'latest_position_transaction_id': self._int_or_none(
                    latest_position_tx.get('transaction_id') if latest_position_tx is not None else None
                ),
                'latest_position_created_at': self._int_or_none(
                    latest_position_tx.get('created_at') if latest_position_tx is not None else None
                ),
                'latest_pool_transaction_id': self._int_or_none(
                    latest_pool_tx.get('transaction_id') if latest_pool_tx is not None else None
                ),
                'latest_pool_trade_time_ms': latest_pool_trade_time_ms,
                'latest_pool_liquidity_event_time_ms': latest_pool_liquidity_time_ms,
                'position_basis_snapshot': position_snapshot_summary,
                'pool_state_snapshot': pool_snapshot_summary,
            },
        }

    def _latest_row(self, rows: list[dict] | None) -> dict | None:
        if not rows:
            return None
        return max(
            rows,
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
                str(row.get('transaction_type') or ''),
            ),
        )

    def _latest_created_at(
        self,
        rows: list[dict] | None,
        allowed_types: set[str],
    ) -> int | None:
        timestamps = [
            int(row.get('created_at') or 0)
            for row in (rows or [])
            if row.get('transaction_type') in allowed_types and row.get('created_at') is not None
        ]
        if not timestamps:
            return None
        return max(timestamps)

    def _position_snapshot_summary(
        self,
        snapshot: dict | None,
        *,
        live_metrics: dict,
    ) -> dict | None:
        if snapshot is None:
            return None
        payload = self._payload_dict(snapshot.get('state_payload_json'))
        materialized_protocol_fee_split_case = self._materialized_protocol_fee_split_case(
            snapshot,
            live_metrics=live_metrics,
        )
        unresolved_profile = self.protocol_fee_split_semantics.unresolved_profile(
            materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
            protocol_fee_current_owner_timing_case=self._current_owner_timing_case_summary(payload),
            fee_to_continuity_case=self._fee_to_continuity_field(payload, 'continuity_case'),
            protocol_fee_current_owner_provenance_case=self._string_or_none(
                self._exact_current_principal_field(payload, 'protocol_fee_current_owner_provenance_case')
            ),
        )
        unresolved_semantic = self.protocol_fee_split_semantics.unresolved_semantic(unresolved_profile)
        return {
            'status': snapshot.get('status'),
            'basis_type': snapshot.get('basis_type'),
            'current_liquidity': snapshot.get('current_liquidity'),
            'basis_transaction_id': self._int_or_none(snapshot.get('basis_transaction_id')),
            'basis_time_ms': self._int_or_none(snapshot.get('basis_time_ms')),
            'basis_opens_current_round': bool(payload.get('basis_opens_current_round')),
            'has_only_zero_liquidity_before_basis': bool(payload.get('has_only_zero_liquidity_before_basis')),
            'current_round_liquidity_event_count': self._int_or_none(payload.get('current_round_liquidity_event_count')),
            'current_round_started_at': self._int_or_none(payload.get('current_round_started_at')),
            'current_round_started_transaction_id': self._int_or_none(payload.get('current_round_started_transaction_id')),
            'current_round_trade_count_before_basis': self._int_or_none(
                payload.get('current_round_trade_count_before_basis')
            ),
            'trade_count_between_basis_and_fee_free_basis': self._int_or_none(
                payload.get('trade_count_between_basis_and_fee_free_basis')
            ),
            'exact_current_principal_case': self._exact_current_principal_case(payload),
            'protocol_fee_liquidity_provenance_case': self._protocol_fee_liquidity_provenance_case(payload),
            'basis_protocol_fee_liquidity_minted': self._string_or_none(
                self._exact_current_principal_field(payload, 'basis_protocol_fee_liquidity_minted')
            ),
            'post_basis_protocol_fee_liquidity_minted': self._string_or_none(
                self._exact_current_principal_field(payload, 'post_basis_protocol_fee_liquidity_minted')
            ),
            'post_basis_protocol_fee_mint_event_count': self._int_or_none(
                self._exact_current_principal_field(payload, 'post_basis_protocol_fee_mint_event_count')
            ),
            'post_basis_protocol_fee_liquidity_minted_before_first_add': self._string_or_none(
                self._exact_current_principal_field(payload, 'post_basis_protocol_fee_liquidity_minted_before_first_add')
            ),
            'fee_to_continuous_protocol_fee_liquidity_current': self._string_or_none(
                self._exact_current_principal_field(payload, 'fee_to_continuous_protocol_fee_liquidity_current')
            ),
            'protocol_fee_current_owner_provenance_case': self._string_or_none(
                self._exact_current_principal_field(payload, 'protocol_fee_current_owner_provenance_case')
            ),
            'basis_protocol_fee_liquidity_owned_by_current_owner': self._string_or_none(
                self._exact_current_principal_field(payload, 'basis_protocol_fee_liquidity_owned_by_current_owner')
            ),
            'post_basis_protocol_fee_liquidity_owned_by_current_owner': self._string_or_none(
                self._exact_current_principal_field(payload, 'post_basis_protocol_fee_liquidity_owned_by_current_owner')
            ),
            'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': self._string_or_none(
                self._exact_current_principal_field(
                    payload,
                    'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add',
                )
            ),
            'protocol_fee_liquidity_owned_by_current_owner_current': self._string_or_none(
                self._exact_current_principal_field(payload, 'protocol_fee_liquidity_owned_by_current_owner_current')
            ),
            'protocol_fee_liquidity_owned_by_other_accounts': self._string_or_none(
                self._exact_current_principal_field(payload, 'protocol_fee_liquidity_owned_by_other_accounts')
            ),
            'protocol_fee_liquidity_owner_unknown': self._string_or_none(
                self._exact_current_principal_field(payload, 'protocol_fee_liquidity_owner_unknown')
            ),
            'fee_to_continuity_case': self._fee_to_continuity_field(payload, 'continuity_case'),
            'fee_to_continuity_change_count_after_basis': self._int_or_none(
                self._fee_to_continuity_field(payload, 'change_count_after_basis')
            ),
            'fee_to_continuity_known_before_basis': self._bool_or_none(
                self._fee_to_continuity_field(payload, 'known_before_basis')
            ),
            'fee_to_account_at_basis': self._string_or_none(
                self._fee_to_continuity_field(payload, 'fee_to_account_at_basis')
            ),
            'fee_to_account_latest_known': self._string_or_none(
                self._fee_to_continuity_field(payload, 'fee_to_account_latest_known')
            ),
            'materialized_protocol_fee_split_case': materialized_protocol_fee_split_case,
            'protocol_fee_split_semantic': self.protocol_fee_split_semantics.semantic_for_case(
                materialized_protocol_fee_split_case
            ),
            'unresolved_protocol_fee_profile': unresolved_profile,
            'unresolved_protocol_fee_semantic': unresolved_semantic,
            'unresolved_protocol_fee_boundary_status': self.protocol_fee_split_semantics.unresolved_boundary_status(
                unresolved_semantic
            ),
            'unresolved_protocol_fee_explanation': self.protocol_fee_split_semantics.unresolved_explanation(
                unresolved_semantic
            ),
        }

    def _pool_snapshot_summary(self, snapshot: dict | None) -> dict | None:
        if snapshot is None:
            return None
        return {
            'last_transaction_id': self._int_or_none(snapshot.get('last_transaction_id')),
            'last_trade_time_ms': self._int_or_none(snapshot.get('last_trade_time_ms')),
            'last_liquidity_event_time_ms': self._int_or_none(snapshot.get('last_liquidity_event_time_ms')),
        }

    def _readiness(
        self,
        *,
        comparable: bool,
        mismatch_codes: list[str],
        live_metrics: dict,
        position_snapshot_summary: dict | None,
    ) -> tuple[str, list[str]]:
        if not comparable:
            return 'snapshot_missing', list(mismatch_codes)
        if mismatch_codes:
            return 'structure_mismatch', list(mismatch_codes)
        reasons = []
        if (
            isinstance(position_snapshot_summary, dict)
            and position_snapshot_summary.get('materialized_protocol_fee_split_case')
            == 'fee_to_nonzero_prior_add_basis_unresolved'
        ):
            unresolved_reason_code = self.protocol_fee_split_semantics.unresolved_reason_code(
                materialized_protocol_fee_split_case=position_snapshot_summary.get(
                    'materialized_protocol_fee_split_case'
                ),
                protocol_fee_current_owner_timing_case=self._current_owner_timing_case(
                    position_snapshot_summary
                ),
                fee_to_continuity_case=position_snapshot_summary.get('fee_to_continuity_case'),
                protocol_fee_current_owner_provenance_case=position_snapshot_summary.get(
                    'protocol_fee_current_owner_provenance_case'
                ),
            )
            if unresolved_reason_code is not None:
                reasons.append(unresolved_reason_code)
            reasons.append('materialized_protocol_fee_split_unresolved')
        if not bool(live_metrics.get('exact_fee_supported')):
            reasons.append('exact_fee_not_supported')
        if not bool(live_metrics.get('exact_principal_supported')):
            reasons.append('exact_principal_not_supported')
        reasons.extend(str(code) for code in (live_metrics.get('computation_blockers') or []))
        reasons.extend(str(code) for code in (live_metrics.get('value_warning_codes') or []))
        if reasons:
            return 'financial_semantics_pending', reasons
        return 'candidate', []

    def _decimal_equal(self, left: object, right: object) -> bool:
        if left is None or right is None:
            return left is right
        return Decimal(str(left)) == Decimal(str(right))

    def _int_or_none(self, value: object) -> int | None:
        if value in (None, ''):
            return None
        return int(value)

    def _payload_dict(self, payload: object) -> dict:
        if isinstance(payload, dict):
            return payload
        return {}

    def _exact_current_principal_case(self, payload: dict) -> str | None:
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return None
        value = exact_current_principal.get('exact_current_principal_case')
        if value in (None, ''):
            return None
        return str(value)

    def _protocol_fee_liquidity_provenance_case(self, payload: dict) -> str | None:
        value = self._exact_current_principal_field(payload, 'protocol_fee_liquidity_provenance_case')
        if value in (None, ''):
            return None
        return str(value)

    def _current_owner_timing_case_summary(self, payload: dict) -> str:
        basis_owned = self._decimal_or_none(
            self._exact_current_principal_field(payload, 'basis_protocol_fee_liquidity_owned_by_current_owner')
        ) or Decimal('0')
        post_basis_owned = self._decimal_or_none(
            self._exact_current_principal_field(payload, 'post_basis_protocol_fee_liquidity_owned_by_current_owner')
        ) or Decimal('0')
        post_basis_owned_before_first_add = self._decimal_or_none(
            self._exact_current_principal_field(
                payload,
                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add',
            )
        ) or Decimal('0')
        if basis_owned == 0 and post_basis_owned == 0 and post_basis_owned_before_first_add == 0:
            return 'no_current_owner_protocol_fee'
        if post_basis_owned_before_first_add > post_basis_owned:
            return 'inconsistent_before_first_add_exceeds_post_basis'
        if basis_owned > 0 and post_basis_owned == 0:
            return 'basis_only'
        if basis_owned == 0 and post_basis_owned > 0:
            if post_basis_owned_before_first_add == post_basis_owned:
                return 'post_basis_only_before_first_add_only'
            return 'post_basis_only_with_later_add_present'
        if basis_owned > 0 and post_basis_owned > 0:
            if post_basis_owned_before_first_add == post_basis_owned:
                return 'basis_and_post_basis_before_first_add_only'
            return 'basis_and_post_basis_with_later_add_present'
        return 'unknown_or_partial'

    def _current_owner_timing_case(self, snapshot_summary: dict) -> str:
        basis_owned = self._decimal_or_none(
            snapshot_summary.get('basis_protocol_fee_liquidity_owned_by_current_owner')
        ) or Decimal('0')
        post_basis_owned = self._decimal_or_none(
            snapshot_summary.get('post_basis_protocol_fee_liquidity_owned_by_current_owner')
        ) or Decimal('0')
        post_basis_owned_before_first_add = self._decimal_or_none(
            snapshot_summary.get('post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add')
        ) or Decimal('0')
        if basis_owned == 0 and post_basis_owned == 0 and post_basis_owned_before_first_add == 0:
            return 'no_current_owner_protocol_fee'
        if post_basis_owned_before_first_add > post_basis_owned:
            return 'inconsistent_before_first_add_exceeds_post_basis'
        if basis_owned > 0 and post_basis_owned == 0:
            return 'basis_only'
        if basis_owned == 0 and post_basis_owned > 0:
            if post_basis_owned_before_first_add == post_basis_owned:
                return 'post_basis_only_before_first_add_only'
            return 'post_basis_only_with_later_add_present'
        if basis_owned > 0 and post_basis_owned > 0:
            if post_basis_owned_before_first_add == post_basis_owned:
                return 'basis_and_post_basis_before_first_add_only'
            return 'basis_and_post_basis_with_later_add_present'
        return 'unknown_or_partial'

    def _exact_current_principal_field(self, payload: dict, field_name: str) -> object:
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return None
        return exact_current_principal.get(field_name)

    def _fee_to_continuity_field(self, payload: dict, field_name: str) -> object:
        continuity = payload.get('fee_to_continuity')
        if not isinstance(continuity, dict):
            return None
        return continuity.get(field_name)

    def _materialized_protocol_fee_split_case(
        self,
        snapshot: dict,
        *,
        live_metrics: dict,
    ) -> str | None:
        live_liquidity = self._decimal_or_none(live_metrics.get('position_liquidity_live'))
        tracked_liquidity = self._decimal_or_none(snapshot.get('current_liquidity'))
        if live_liquidity is None or tracked_liquidity is None or live_liquidity <= tracked_liquidity:
            return None
        if self._safe_all_protocol_fee_mints_owned_by_current_owner(
            snapshot,
            live_liquidity=live_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'all_protocol_fee_mints_owned_by_current_owner'
        if self._safe_current_owner_protocol_fee_component_proven(
            snapshot,
            live_liquidity=live_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'current_owner_protocol_fee_component_proven'
        if not bool(live_metrics.get('owner_is_fee_to')):
            return 'owner_not_fee_to'
        basis_type = str(snapshot.get('basis_type') or '')
        if basis_type == 'remove_liquidity':
            return 'fee_to_latest_remove_basis'
        prior_liquidity_before_basis = self._prior_liquidity_before_basis(snapshot)
        if prior_liquidity_before_basis == Decimal('0'):
            return 'fee_to_opening_add_from_zero'
        if self._safe_fee_to_basis_only_nonzero_prior_add_basis(
            snapshot,
            live_liquidity=live_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'fee_to_basis_only_nonzero_prior_add_basis'
        if self._safe_fee_to_continuous_nonzero_prior_add_basis(
            snapshot,
            live_liquidity=live_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'fee_to_continuous_nonzero_prior_add_basis'
        if self._post_basis_remove_count(snapshot) > 0:
            return 'fee_to_nonzero_prior_add_basis_unresolved'
        if self._exact_current_principal_case(self._payload_dict(snapshot.get('state_payload_json'))) is not None:
            return 'fee_to_materialized_nonzero_prior_add_basis'
        return 'fee_to_nonzero_prior_add_basis_unresolved'

    def _prior_liquidity_before_basis(self, snapshot: dict) -> Decimal:
        payload = self._payload_dict(snapshot.get('state_payload_json'))
        value = payload.get('prior_liquidity_before_basis')
        decimal_value = self._decimal_or_none(value)
        if decimal_value is None:
            return Decimal('0')
        return decimal_value

    def _post_basis_remove_count(self, snapshot: dict) -> int:
        payload = self._payload_dict(snapshot.get('state_payload_json'))
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return 0
        value = exact_current_principal.get('post_basis_remove_count')
        if value in (None, ''):
            return 0
        return int(value)

    def _safe_fee_to_continuous_nonzero_prior_add_basis(
        self,
        snapshot: dict,
        *,
        live_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> bool:
        payload = self._payload_dict(snapshot.get('state_payload_json'))
        if self._fee_to_continuity_field(payload, 'continuity_case') != 'continuous_no_changes_after_basis':
            return False
        owner = self._string_or_none(self._fee_to_continuity_field(payload, 'owner'))
        if owner in (None, ''):
            return False
        if self._fee_to_continuity_field(payload, 'fee_to_account_at_basis') != owner:
            return False
        if self._fee_to_continuity_field(payload, 'fee_to_account_latest_known') != owner:
            return False
        protocol_fee_liquidity = self._decimal_or_none(
            self._exact_current_principal_field(payload, 'fee_to_continuous_protocol_fee_liquidity_current')
        )
        if protocol_fee_liquidity is None or protocol_fee_liquidity <= Decimal('0'):
            return False
        return self._decimal_equal(live_liquidity, tracked_liquidity + protocol_fee_liquidity)

    def _safe_fee_to_basis_only_nonzero_prior_add_basis(
        self,
        snapshot: dict,
        *,
        live_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> bool:
        payload = self._payload_dict(snapshot.get('state_payload_json'))
        if self._bool_or_none(self._fee_to_continuity_field(payload, 'known_before_basis')) is not True:
            return False
        owner = self._string_or_none(self._fee_to_continuity_field(payload, 'owner'))
        if owner in (None, ''):
            return False
        if self._fee_to_continuity_field(payload, 'fee_to_account_at_basis') != owner:
            return False
        if self._protocol_fee_liquidity_provenance_case(payload) != 'basis_only_mints':
            return False
        protocol_fee_liquidity = self._decimal_or_none(
            self._exact_current_principal_field(payload, 'basis_protocol_fee_liquidity_minted')
        )
        if protocol_fee_liquidity is None or protocol_fee_liquidity <= Decimal('0'):
            return False
        return self._decimal_equal(live_liquidity, tracked_liquidity + protocol_fee_liquidity)

    def _safe_all_protocol_fee_mints_owned_by_current_owner(
        self,
        snapshot: dict,
        *,
        live_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> bool:
        payload = self._payload_dict(snapshot.get('state_payload_json'))
        if self._string_or_none(
            self._exact_current_principal_field(payload, 'protocol_fee_current_owner_provenance_case')
        ) != 'all_mints_owned_by_current_owner':
            return False
        owned_by_current_owner = self._decimal_or_none(
            self._exact_current_principal_field(payload, 'protocol_fee_liquidity_owned_by_current_owner_current')
        )
        owned_by_other_accounts = self._decimal_or_none(
            self._exact_current_principal_field(payload, 'protocol_fee_liquidity_owned_by_other_accounts')
        )
        owner_unknown = self._decimal_or_none(
            self._exact_current_principal_field(payload, 'protocol_fee_liquidity_owner_unknown')
        )
        if owned_by_current_owner is None or owned_by_current_owner <= Decimal('0'):
            return False
        if owned_by_other_accounts not in (None, Decimal('0')):
            return False
        if owner_unknown not in (None, Decimal('0')):
            return False
        return self._decimal_equal(live_liquidity, tracked_liquidity + owned_by_current_owner)

    def _safe_current_owner_protocol_fee_component_proven(
        self,
        snapshot: dict,
        *,
        live_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> bool:
        payload = self._payload_dict(snapshot.get('state_payload_json'))
        owned_by_current_owner = self._decimal_or_none(
            self._exact_current_principal_field(payload, 'protocol_fee_liquidity_owned_by_current_owner_current')
        )
        if owned_by_current_owner is None or owned_by_current_owner <= Decimal('0'):
            return False
        return self._decimal_equal(live_liquidity, tracked_liquidity + owned_by_current_owner)

    def _decimal_or_none(self, value: object) -> Decimal | None:
        if value in (None, ''):
            return None
        return Decimal(str(value))

    def _string_or_none(self, value: object) -> str | None:
        if value in (None, ''):
            return None
        return str(value)

    def _bool_or_none(self, value: object) -> bool | None:
        if value in (None, ''):
            return None
        return bool(value)
