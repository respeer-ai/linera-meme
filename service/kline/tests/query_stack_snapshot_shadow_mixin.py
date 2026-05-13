class QueryStackSnapshotShadowMixin:
    def test_snapshot_shadow_evaluator_marks_unresolved_nonzero_prior_add_basis_fee_to_case(self):
        result = self._evaluate(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'status': 'active',
                'current_liquidity': '10',
            },
            projected_metrics={
                'metrics_status': 'partial_projected_redeemable_only',
                'fee_calculation_complete': False,
                'principal_calculation_complete': False,
                'position_liquidity': '12',
                'owner_receives_protocol_fees': True,
                'computation_blockers': ['missing_protocol_fee_provenance'],
                'value_warning_codes': [],
            },
            replay_summary={
                'latest_position_transaction_id': 10,
                'latest_position_created_at': 1000,
                'latest_pool_transaction_id': 12,
                'latest_pool_trade_time_ms': None,
                'latest_pool_liquidity_event_time_ms': 1200,
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'fee_to_continuity': {
                        'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'continuity_case': 'changed_after_basis',
                        'change_count_after_basis': 1,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'fee_to_account_latest_known': '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee@chain-fee',
                    },
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'exact_current_principal': {
                        'principal_amount_0_current': '5',
                        'principal_amount_1_current': '10',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 0,
                        'post_basis_remove_count': 1,
                        'basis_protocol_fee_liquidity_owned_by_current_owner': '2',
                        'post_basis_protocol_fee_liquidity_owned_by_current_owner': '0',
                        'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '0',
                        'protocol_fee_current_owner_provenance_case': 'owner_and_non_owner_mints',
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 12,
                'last_trade_time_ms': None,
                'last_liquidity_event_time_ms': 1200,
            },
        )

        self.assertEqual(
            result['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_nonzero_prior_add_basis_unresolved',
        )
        self.assertEqual(
            result['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'fee_to_nonzero_prior_add_unresolved',
        )
        self.assertEqual(
            result['snapshot_shadow']['readiness_reason_codes'],
            [
                'unresolved_fee_to_nonzero_prior_add__basis_only__changed_after_basis__owner_and_non_owner_mints',
                'materialized_protocol_fee_split_unresolved',
                'fee_calculation_incomplete',
                'principal_calculation_incomplete',
                'missing_protocol_fee_provenance',
            ],
        )

    def test_snapshot_shadow_evaluator_marks_safe_continuous_nonzero_prior_add_basis_fee_to_case(self):
        result = self._evaluate(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'status': 'active',
                'current_liquidity': '10',
            },
            projected_metrics={
                'metrics_status': 'exact_no_swap_history',
                'fee_calculation_complete': True,
                'principal_calculation_complete': True,
                'position_liquidity': '12',
                'owner_receives_protocol_fees': True,
                'computation_blockers': [],
                'value_warning_codes': [],
            },
            replay_summary={
                'latest_position_transaction_id': 10,
                'latest_position_created_at': 1000,
                'latest_pool_transaction_id': 12,
                'latest_pool_trade_time_ms': None,
                'latest_pool_liquidity_event_time_ms': 1200,
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'fee_to_continuity': {
                        'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'continuity_case': 'continuous_no_changes_after_basis',
                        'change_count_after_basis': 0,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'fee_to_account_latest_known': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                    },
                    'exact_current_principal': {
                        'principal_amount_0_current': '5',
                        'principal_amount_1_current': '10',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 1,
                        'post_basis_remove_count': 0,
                        'fee_to_continuous_protocol_fee_liquidity_current': '2',
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 12,
                'last_trade_time_ms': None,
                'last_liquidity_event_time_ms': 1200,
            },
        )

        self.assertEqual(
            result['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_continuous_nonzero_prior_add_basis',
        )
        self.assertEqual(
            result['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'fee_to_continuous_nonzero_prior_add_exact',
        )
        self.assertEqual(result['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(result['snapshot_shadow']['readiness_reason_codes'], [])

    def test_snapshot_shadow_evaluator_marks_basis_only_nonzero_prior_add_basis_fee_to_case_as_candidate(self):
        result = self._evaluate(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'status': 'active',
                'current_liquidity': '10',
            },
            projected_metrics={
                'metrics_status': 'exact_no_swap_history',
                'fee_calculation_complete': True,
                'principal_calculation_complete': True,
                'position_liquidity': '12',
                'owner_receives_protocol_fees': True,
                'computation_blockers': [],
                'value_warning_codes': [],
            },
            replay_summary={
                'latest_position_transaction_id': 10,
                'latest_position_created_at': 1000,
                'latest_pool_transaction_id': 12,
                'latest_pool_trade_time_ms': None,
                'latest_pool_liquidity_event_time_ms': 1200,
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'fee_to_continuity': {
                        'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'continuity_case': 'changed_after_basis',
                        'change_count_after_basis': 2,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'fee_to_account_latest_known': '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee@chain-fee',
                    },
                    'exact_current_principal': {
                        'principal_amount_0_current': '5',
                        'principal_amount_1_current': '10',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 1,
                        'post_basis_remove_count': 0,
                        'basis_protocol_fee_liquidity_minted': '2',
                        'post_basis_protocol_fee_liquidity_minted': '0',
                        'post_basis_protocol_fee_mint_event_count': 0,
                        'post_basis_protocol_fee_liquidity_minted_before_first_add': '0',
                        'fee_to_continuous_protocol_fee_liquidity_current': '2',
                        'protocol_fee_liquidity_provenance_case': 'basis_only_mints',
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 12,
                'last_trade_time_ms': None,
                'last_liquidity_event_time_ms': 1200,
            },
        )

        self.assertEqual(
            result['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_basis_only_nonzero_prior_add_basis',
        )
        self.assertEqual(
            result['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'fee_to_basis_only_nonzero_prior_add_exact',
        )
        self.assertEqual(result['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(result['snapshot_shadow']['readiness_reason_codes'], [])
