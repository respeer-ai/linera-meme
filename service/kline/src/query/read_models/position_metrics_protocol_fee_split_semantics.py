class PositionMetricsProtocolFeeSplitSemantics:
    def semantic_for_case(self, case: object) -> str:
        return {
            None: 'not_applicable_or_unknown',
            '': 'not_applicable_or_unknown',
            'owner_not_fee_to': 'non_fee_to_owner',
            'fee_to_opening_add_from_zero': 'fee_to_opening_add_from_zero_exact',
            'fee_to_latest_remove_basis': 'fee_to_latest_remove_basis_exact',
            'fee_to_basis_only_nonzero_prior_add_basis': 'fee_to_basis_only_nonzero_prior_add_exact',
            'fee_to_materialized_nonzero_prior_add_basis': 'fee_to_materialized_nonzero_prior_add_exact',
            'fee_to_continuous_nonzero_prior_add_basis': 'fee_to_continuous_nonzero_prior_add_exact',
            'all_protocol_fee_mints_owned_by_current_owner': 'historical_protocol_fee_mints_owned_by_current_owner_exact',
            'current_owner_protocol_fee_component_proven': 'historical_protocol_fee_component_owned_by_current_owner_exact',
            'fee_to_nonzero_prior_add_basis_unresolved': 'fee_to_nonzero_prior_add_unresolved',
        }.get(case, 'unclassified')

    def is_safe_restored_case(self, case: object) -> bool:
        return case in {
            'fee_to_basis_only_nonzero_prior_add_basis',
            'fee_to_continuous_nonzero_prior_add_basis',
        }

    def unresolved_profile(
        self,
        *,
        materialized_protocol_fee_split_case: object,
        protocol_fee_current_owner_timing_case: object,
        fee_to_continuity_case: object,
        protocol_fee_current_owner_provenance_case: object,
    ) -> str | None:
        if materialized_protocol_fee_split_case != 'fee_to_nonzero_prior_add_basis_unresolved':
            return None
        return '|'.join([
            str(protocol_fee_current_owner_timing_case or 'unknown_timing'),
            str(fee_to_continuity_case or 'unknown_continuity'),
            str(protocol_fee_current_owner_provenance_case or 'unknown_provenance'),
        ])

    def unresolved_reason_code(
        self,
        *,
        materialized_protocol_fee_split_case: object,
        protocol_fee_current_owner_timing_case: object,
        fee_to_continuity_case: object,
        protocol_fee_current_owner_provenance_case: object,
    ) -> str | None:
        profile = self.unresolved_profile(
            materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
            protocol_fee_current_owner_timing_case=protocol_fee_current_owner_timing_case,
            fee_to_continuity_case=fee_to_continuity_case,
            protocol_fee_current_owner_provenance_case=protocol_fee_current_owner_provenance_case,
        )
        if profile is None:
            return None
        timing_case, continuity_case, provenance_case = profile.split('|', 2)
        return '__'.join([
            'unresolved_fee_to_nonzero_prior_add',
            timing_case,
            continuity_case,
            provenance_case,
        ])

    def unresolved_semantic(self, profile: object) -> str:
        return {
            None: 'not_applicable_or_unknown',
            '': 'not_applicable_or_unknown',
            (
                'basis_only|changed_after_basis|owner_and_non_owner_mints'
            ): 'current_owner_basis_protocol_fee_known_but_fee_to_changed_and_non_owner_mints_present',
        }.get(profile, 'unclassified_unresolved_profile')

    def unresolved_explanation(self, semantic: object) -> str | None:
        return {
            'current_owner_basis_protocol_fee_known_but_fee_to_changed_and_non_owner_mints_present': (
                'The current owner basis protocol-fee component is known, but fee_to changed after basis and'
                ' protocol-fee mints for non-owner accounts are also present, so the snapshot cannot prove'
                ' which later fee dilution belongs to this position.'
            ),
            None: None,
            '': None,
            'not_applicable_or_unknown': None,
            'unclassified_unresolved_profile': None,
        }.get(semantic, None)

    def unresolved_boundary_status(self, semantic: object) -> str:
        return {
            None: 'not_applicable_or_unknown',
            '': 'not_applicable_or_unknown',
            'not_applicable_or_unknown': 'not_applicable_or_unknown',
            'unclassified_unresolved_profile': 'needs_more_provenance_design',
            'current_owner_basis_protocol_fee_known_but_fee_to_changed_and_non_owner_mints_present': (
                'unsupported_in_current_snapshot_model'
            ),
        }.get(semantic, 'needs_more_provenance_design')
