from decimal import Decimal
from query.read_models.position_metrics_protocol_fee_split_semantics import PositionMetricsProtocolFeeSplitSemantics
from query.read_models.position_metrics_replay_summary import PositionMetricsReplaySummary
from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot
from query.read_models.position_metrics_snapshot_semantic_facts import PositionMetricsSnapshotSemanticFacts
from query.read_models.position_metrics_snapshot_shadow_payload_builder import PositionMetricsSnapshotShadowPayloadBuilder


class PositionMetricsSnapshotShadowEvaluator:
    def __init__(
        self,
        *,
        protocol_fee_split_semantics: PositionMetricsProtocolFeeSplitSemantics | None = None,
        payload_builder: PositionMetricsSnapshotShadowPayloadBuilder | None = None,
    ):
        self.protocol_fee_split_semantics = protocol_fee_split_semantics or PositionMetricsProtocolFeeSplitSemantics()
        self.payload_builder = payload_builder or PositionMetricsSnapshotShadowPayloadBuilder()

    def evaluate(
        self,
        *,
        position: dict,
        projected_metrics: dict,
        replay_summary,
        position_basis_snapshot: dict | None,
        pool_state_snapshot: dict | None,
    ) -> dict:
        replay_summary = self._replay_summary(replay_summary)
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        pool_state_snapshot = self._pool_state_snapshot(pool_state_snapshot)
        latest_markers = replay_summary.shadow_latest_dict()
        latest_position_transaction_id = latest_markers.get('latest_position_transaction_id')
        latest_position_created_at = latest_markers.get('latest_position_created_at')
        latest_pool_transaction_id = latest_markers.get('latest_pool_transaction_id')
        latest_pool_trade_time_ms = latest_markers.get('latest_pool_trade_time_ms')
        latest_pool_liquidity_time_ms = latest_markers.get('latest_pool_liquidity_event_time_ms')
        mismatch_codes = []

        if position_basis_snapshot.raw() is None:
            mismatch_codes.append('missing_position_basis_snapshot')
        if pool_state_snapshot.raw() is None:
            mismatch_codes.append('missing_pool_state_snapshot')

        if position_basis_snapshot.raw() is not None:
            if str(position_basis_snapshot.status() or '') != str(position.get('status') or ''):
                mismatch_codes.append('position_status_mismatch')
            if not self._decimal_equal(
                position_basis_snapshot.current_liquidity(),
                position.get('current_liquidity'),
            ):
                mismatch_codes.append('position_current_liquidity_mismatch')
            if latest_position_transaction_id is not None:
                if self._int_or_none(position_basis_snapshot.basis_transaction_id()) != latest_position_transaction_id:
                    mismatch_codes.append('position_basis_transaction_id_mismatch')
                if self._int_or_none(position_basis_snapshot.basis_time_ms()) != latest_position_created_at:
                    mismatch_codes.append('position_basis_time_mismatch')

        if pool_state_snapshot.raw() is not None:
            if latest_pool_transaction_id is not None:
                if self._int_or_none(pool_state_snapshot.last_transaction_id()) != latest_pool_transaction_id:
                    mismatch_codes.append('pool_last_transaction_id_mismatch')
            if self._int_or_none(pool_state_snapshot.last_trade_time_ms()) != latest_pool_trade_time_ms:
                mismatch_codes.append('pool_last_trade_time_mismatch')
            if self._int_or_none(pool_state_snapshot.last_liquidity_event_time_ms()) != latest_pool_liquidity_time_ms:
                mismatch_codes.append('pool_last_liquidity_event_time_mismatch')

        position_snapshot_summary = self._position_snapshot_summary(
            position_basis_snapshot,
            projected_metrics=projected_metrics,
        )
        pool_snapshot_summary = self.build_pool_snapshot_summary(pool_state_snapshot)
        comparable = position_basis_snapshot.raw() is not None and pool_state_snapshot.raw() is not None
        readiness, readiness_reason_codes = self._readiness(
            comparable=comparable,
            mismatch_codes=mismatch_codes,
            projected_metrics=projected_metrics,
            position_snapshot_summary=position_snapshot_summary,
        )
        return self.payload_builder.build(
            position=position,
            projected_metrics=projected_metrics,
            fee_calculation_complete=bool(projected_metrics.get('fee_calculation_complete')),
            principal_calculation_complete=bool(projected_metrics.get('principal_calculation_complete')),
            snapshot_shadow={
                'comparable': comparable,
                'position_basis_snapshot_present': position_basis_snapshot.raw() is not None,
                'pool_state_snapshot_present': pool_state_snapshot.raw() is not None,
                'mismatch_codes': mismatch_codes,
                'readiness': readiness,
                'readiness_reason_codes': readiness_reason_codes,
                'projected_position_status': position.get('status') or 'active',
                'projected_current_liquidity': position.get('current_liquidity'),
                'projected_metrics_status': projected_metrics.get('metrics_status'),
                'computation_blockers': list(projected_metrics.get('computation_blockers') or []),
                'value_warning_codes': list(projected_metrics.get('value_warning_codes') or []),
                **latest_markers,
                'position_basis_snapshot': position_snapshot_summary,
                'pool_state_snapshot': pool_snapshot_summary,
            },
        )

    def evaluate_candidate(
        self,
        *,
        position: dict,
        projected_metrics: dict,
        exact_case: str,
        position_basis_snapshot,
        pool_state_snapshot,
    ) -> dict:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        pool_state_snapshot = self._pool_state_snapshot(pool_state_snapshot)
        return self.payload_builder.build(
            position=position,
            projected_metrics=projected_metrics,
            fee_calculation_complete=True,
            principal_calculation_complete=True,
            snapshot_shadow={
                'comparable': True,
                'position_basis_snapshot_present': True,
                'pool_state_snapshot_present': True,
                'mismatch_codes': [],
                'readiness': 'candidate',
                'readiness_reason_codes': [],
                'exact_case': exact_case,
                'projected_position_status': position.get('status') or 'active',
                'projected_current_liquidity': position.get('current_liquidity'),
                'projected_metrics_status': projected_metrics['metrics_status'],
                'computation_blockers': [],
                'value_warning_codes': [],
                **position_basis_snapshot.shadow_latest_dict(),
                **pool_state_snapshot.shadow_latest_dict(),
                'position_basis_snapshot': self.build_position_snapshot_summary(
                    position_basis_snapshot,
                    projected_metrics=projected_metrics,
                ),
                'pool_state_snapshot': self.build_pool_snapshot_summary(
                    pool_state_snapshot
                ),
            },
        )

    def _replay_summary(self, replay_summary) -> PositionMetricsReplaySummary:
        if isinstance(replay_summary, PositionMetricsReplaySummary):
            return replay_summary
        return PositionMetricsReplaySummary(replay_summary)

    def _position_basis_snapshot(self, snapshot) -> PositionMetricsPositionBasisSnapshot:
        if isinstance(snapshot, PositionMetricsPositionBasisSnapshot):
            return snapshot
        return PositionMetricsPositionBasisSnapshot(snapshot)

    def _pool_state_snapshot(self, snapshot) -> PositionMetricsPoolStateSnapshot:
        if isinstance(snapshot, PositionMetricsPoolStateSnapshot):
            return snapshot
        return PositionMetricsPoolStateSnapshot(snapshot)

    def build_position_snapshot_summary(
        self,
        snapshot,
        *,
        projected_metrics: dict,
    ) -> dict | None:
        return self._position_snapshot_summary(
            snapshot,
            projected_metrics=projected_metrics,
        )

    def build_pool_snapshot_summary(self, snapshot) -> dict | None:
        return self._pool_snapshot_summary(snapshot)

    def _position_snapshot_summary(
        self,
        snapshot,
        *,
        projected_metrics: dict,
    ) -> dict | None:
        position_basis_snapshot = self._position_basis_snapshot(snapshot)
        if position_basis_snapshot.raw() is None:
            return None
        summary = position_basis_snapshot.summary_dict()
        materialized_protocol_fee_split_case = self._materialized_protocol_fee_split_case(
            position_basis_snapshot,
            projected_metrics=projected_metrics,
        )
        unresolved_profile = self.protocol_fee_split_semantics.unresolved_profile(
            materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
            protocol_fee_current_owner_timing_case=self._current_owner_timing_case(summary),
            fee_to_continuity_case=summary.get('fee_to_continuity_case'),
            protocol_fee_current_owner_provenance_case=summary.get(
                'protocol_fee_current_owner_provenance_case'
            ),
        )
        unresolved_semantic = self.protocol_fee_split_semantics.unresolved_semantic(unresolved_profile)
        return {
            **summary,
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
        pool_state_snapshot = self._pool_state_snapshot(snapshot)
        return pool_state_snapshot.summary_dict()

    def _readiness(
        self,
        *,
        comparable: bool,
        mismatch_codes: list[str],
        projected_metrics: dict,
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
        if not bool(projected_metrics.get('fee_calculation_complete')):
            reasons.append('fee_calculation_incomplete')
        if not bool(projected_metrics.get('principal_calculation_complete')):
            reasons.append('principal_calculation_incomplete')
        reasons.extend(str(code) for code in (projected_metrics.get('computation_blockers') or []))
        reasons.extend(str(code) for code in (projected_metrics.get('value_warning_codes') or []))
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

    def _materialized_protocol_fee_split_case(
        self,
        snapshot,
        *,
        projected_metrics: dict,
    ) -> str | None:
        current_liquidity = self._decimal_or_none(projected_metrics.get('position_liquidity'))
        position_basis_snapshot = self._position_basis_snapshot(snapshot)
        tracked_liquidity = self._decimal_or_none(position_basis_snapshot.current_liquidity())
        if current_liquidity is None or tracked_liquidity is None or current_liquidity <= tracked_liquidity:
            return None
        if self._safe_all_protocol_fee_mints_owned_by_current_owner(
            snapshot,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'all_protocol_fee_mints_owned_by_current_owner'
        if self._safe_current_owner_protocol_fee_component_proven(
            snapshot,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'current_owner_protocol_fee_component_proven'
        if not bool(projected_metrics.get('owner_receives_protocol_fees')):
            return 'owner_not_fee_to'
        basis_type = str(position_basis_snapshot.basis_type() or '')
        if basis_type == 'remove_liquidity':
            return 'fee_to_latest_remove_basis'
        prior_liquidity_before_basis = self._prior_liquidity_before_basis(snapshot)
        if prior_liquidity_before_basis == Decimal('0'):
            return 'fee_to_opening_add_from_zero'
        if self._safe_fee_to_basis_only_nonzero_prior_add_basis(
            snapshot,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'fee_to_basis_only_nonzero_prior_add_basis'
        if self._safe_fee_to_continuous_nonzero_prior_add_basis(
            snapshot,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'fee_to_continuous_nonzero_prior_add_basis'
        if self._post_basis_remove_count(snapshot) > 0:
            return 'fee_to_nonzero_prior_add_basis_unresolved'
        if self._semantic_facts(snapshot).exact_current_principal_case() is not None:
            return 'fee_to_materialized_nonzero_prior_add_basis'
        return 'fee_to_nonzero_prior_add_basis_unresolved'

    def _prior_liquidity_before_basis(self, snapshot: dict) -> Decimal:
        value = self._position_basis_snapshot(snapshot).prior_liquidity_before_basis()
        decimal_value = self._decimal_or_none(value)
        if decimal_value is None:
            return Decimal('0')
        return decimal_value

    def _post_basis_remove_count(self, snapshot) -> int:
        return self._position_basis_snapshot(snapshot).post_basis_remove_count()

    def _safe_fee_to_continuous_nonzero_prior_add_basis(
        self,
        snapshot,
        *,
        current_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> bool:
        facts = self._semantic_facts(snapshot)
        if facts.fee_to_continuity_case() != 'continuous_no_changes_after_basis':
            return False
        owner = facts.fee_to_continuity_owner()
        if owner in (None, ''):
            return False
        if facts.fee_to_account_at_basis() != owner:
            return False
        if facts.fee_to_account_latest_known() != owner:
            return False
        protocol_fee_liquidity = self._decimal_or_none(
            facts.fee_to_continuous_protocol_fee_liquidity_current()
        )
        if protocol_fee_liquidity is None or protocol_fee_liquidity <= Decimal('0'):
            return False
        return self._decimal_equal(current_liquidity, tracked_liquidity + protocol_fee_liquidity)

    def _safe_fee_to_basis_only_nonzero_prior_add_basis(
        self,
        snapshot,
        *,
        current_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> bool:
        facts = self._semantic_facts(snapshot)
        if facts.fee_to_continuity_known_before_basis() is not True:
            return False
        owner = facts.fee_to_continuity_owner()
        if owner in (None, ''):
            return False
        if facts.fee_to_account_at_basis() != owner:
            return False
        if facts.protocol_fee_liquidity_provenance_case() != 'basis_only_mints':
            return False
        protocol_fee_liquidity = self._decimal_or_none(
            facts.basis_protocol_fee_liquidity_minted()
        )
        if protocol_fee_liquidity is None or protocol_fee_liquidity <= Decimal('0'):
            return False
        return self._decimal_equal(current_liquidity, tracked_liquidity + protocol_fee_liquidity)

    def _safe_all_protocol_fee_mints_owned_by_current_owner(
        self,
        snapshot,
        *,
        current_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> bool:
        facts = self._semantic_facts(snapshot)
        if facts.protocol_fee_current_owner_provenance_case() != 'all_mints_owned_by_current_owner':
            return False
        owned_by_current_owner = self._decimal_or_none(
            facts.protocol_fee_liquidity_owned_by_current_owner_current()
        )
        owned_by_other_accounts = self._decimal_or_none(
            facts.protocol_fee_liquidity_owned_by_other_accounts()
        )
        owner_unknown = self._decimal_or_none(
            facts.protocol_fee_liquidity_owner_unknown()
        )
        if owned_by_current_owner is None or owned_by_current_owner <= Decimal('0'):
            return False
        if owned_by_other_accounts not in (None, Decimal('0')):
            return False
        if owner_unknown not in (None, Decimal('0')):
            return False
        return self._decimal_equal(current_liquidity, tracked_liquidity + owned_by_current_owner)

    def _safe_current_owner_protocol_fee_component_proven(
        self,
        snapshot,
        *,
        current_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> bool:
        facts = self._semantic_facts(snapshot)
        owned_by_current_owner = self._decimal_or_none(
            facts.protocol_fee_liquidity_owned_by_current_owner_current()
        )
        if owned_by_current_owner is None or owned_by_current_owner <= Decimal('0'):
            return False
        return self._decimal_equal(current_liquidity, tracked_liquidity + owned_by_current_owner)

    def _semantic_facts(self, snapshot) -> PositionMetricsSnapshotSemanticFacts:
        return self._position_basis_snapshot(snapshot).semantic_facts()

    def _semantic_fact(self, snapshot, field_name: str) -> object:
        return self._semantic_facts(snapshot).get(field_name)

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
