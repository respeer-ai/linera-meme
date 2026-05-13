class QueryStackSnapshotFastPathFeeToMixin:
    def test_snapshot_fast_path_supports_fee_to_public_account_string(self):
        result = self._resolve(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee'},
                    'totalSupply': '10',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '10', 'amount0': '5', 'amount1': '10'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                    'current_round_trade_count_before_basis': 0,
                    'trade_count_between_basis_and_fee_free_basis': 0,
                    'fee_to_continuity': {
                        'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'continuity_case': 'continuous_no_changes_after_basis',
                        'change_count_after_basis': 0,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'fee_to_account_latest_known': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 10,
                'last_trade_time_ms': None,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 10,
                'fee_free_basis_time_ms': 1000,
                'fee_free_reserve_0': '5',
                'fee_free_reserve_1': '10',
                'fee_free_total_supply': '10',
            },
        )

        self.assertIsNotNone(result)
        self.assertTrue(result['projected_metrics']['owner_receives_protocol_fees'])

    def test_snapshot_fast_path_rejects_materialized_nonzero_prior_add_basis_fee_to_case(self):
        result = self._resolve(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'}},
                    'totalSupply': '12',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '12', 'amount0': '6', 'amount1': '12'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'basis_opens_current_round': False,
                    'current_round_trade_count_before_basis': 0,
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'fee_to_continuity': {
                        'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'continuity_case': 'unknown_missing_pre_basis_anchor',
                        'change_count_after_basis': 0,
                        'known_before_basis': False,
                        'fee_to_account_at_basis': None,
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
                'last_trade_time_ms': 1100,
                'last_liquidity_event_time_ms': 1200,
                'fee_free_basis_transaction_id': 12,
                'fee_free_basis_time_ms': 1200,
                'fee_free_reserve_0': '6',
                'fee_free_reserve_1': '12',
                'fee_free_total_supply': '12',
            },
        )

        self.assertIsNone(result)

    def test_snapshot_fast_path_supports_materialized_nonzero_prior_add_basis_fee_to_case_when_continuity_is_safe(self):
        result = self._resolve(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'}},
                    'totalSupply': '12',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '12', 'amount0': '6', 'amount1': '12'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'basis_opens_current_round': False,
                    'current_round_trade_count_before_basis': 0,
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
                'last_trade_time_ms': 1100,
                'last_liquidity_event_time_ms': 1200,
                'fee_free_basis_transaction_id': 12,
                'fee_free_basis_time_ms': 1200,
                'fee_free_reserve_0': '6',
                'fee_free_reserve_1': '12',
                'fee_free_total_supply': '12',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '5')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '10')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_continuous_nonzero_prior_add_basis',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'fee_to_continuous_nonzero_prior_add_exact',
        )

    def test_snapshot_fast_path_supports_materialized_nonzero_prior_add_basis_fee_to_case_when_basis_only_mint_is_proven(self):
        result = self._resolve(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'}},
                    'totalSupply': '12',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '12', 'amount0': '6', 'amount1': '12'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'basis_opens_current_round': False,
                    'current_round_trade_count_before_basis': 0,
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
                'last_trade_time_ms': 1100,
                'last_liquidity_event_time_ms': 1200,
                'fee_free_basis_transaction_id': 12,
                'fee_free_basis_time_ms': 1200,
                'fee_free_reserve_0': '6',
                'fee_free_reserve_1': '12',
                'fee_free_total_supply': '12',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '5')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '10')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_basis_only_nonzero_prior_add_basis',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'fee_to_basis_only_nonzero_prior_add_exact',
        )

    def test_snapshot_fast_path_supports_historical_protocol_fee_mints_owned_by_current_owner(self):
        result = self._resolve(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'}},
                    'totalSupply': '12',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '12', 'amount0': '6', 'amount1': '12'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'basis_opens_current_round': False,
                    'current_round_trade_count_before_basis': 1,
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'fee_to_continuity': {
                        'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                        'continuity_case': 'changed_after_basis',
                        'change_count_after_basis': 1,
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
                        'basis_protocol_fee_liquidity_owned_by_current_owner': '2',
                        'post_basis_protocol_fee_liquidity_owned_by_current_owner': '0',
                        'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '0',
                        'protocol_fee_liquidity_owned_by_current_owner_current': '2',
                        'protocol_fee_liquidity_owned_by_other_accounts': '0',
                        'protocol_fee_liquidity_owner_unknown': '0',
                        'protocol_fee_current_owner_provenance_case': 'all_mints_owned_by_current_owner',
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 12,
                'last_trade_time_ms': 1100,
                'last_liquidity_event_time_ms': 1200,
                'fee_free_basis_transaction_id': 12,
                'fee_free_basis_time_ms': 1200,
                'fee_free_reserve_0': '6',
                'fee_free_reserve_1': '12',
                'fee_free_total_supply': '12',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '5')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '10')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'all_protocol_fee_mints_owned_by_current_owner',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'historical_protocol_fee_mints_owned_by_current_owner_exact',
        )

    def test_snapshot_fast_path_supports_proven_current_owner_protocol_fee_component(self):
        result = self._resolve(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'}},
                    'totalSupply': '12',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '12', 'amount0': '6', 'amount1': '12'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'basis_opens_current_round': False,
                    'current_round_trade_count_before_basis': 1,
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
                        'post_basis_protocol_fee_liquidity_minted': '3',
                        'post_basis_protocol_fee_mint_event_count': 1,
                        'post_basis_protocol_fee_liquidity_minted_before_first_add': '3',
                        'fee_to_continuous_protocol_fee_liquidity_current': '5',
                        'protocol_fee_liquidity_provenance_case': 'basis_and_post_basis_mints',
                        'basis_protocol_fee_liquidity_owned_by_current_owner': '2',
                        'post_basis_protocol_fee_liquidity_owned_by_current_owner': '0',
                        'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '0',
                        'protocol_fee_liquidity_owned_by_current_owner_current': '2',
                        'protocol_fee_liquidity_owned_by_other_accounts': '3',
                        'protocol_fee_liquidity_owner_unknown': '0',
                        'protocol_fee_current_owner_provenance_case': 'owner_and_non_owner_mints',
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 12,
                'last_trade_time_ms': 1100,
                'last_liquidity_event_time_ms': 1200,
                'fee_free_basis_transaction_id': 12,
                'fee_free_basis_time_ms': 1200,
                'fee_free_reserve_0': '6',
                'fee_free_reserve_1': '12',
                'fee_free_total_supply': '12',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '5')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '10')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'current_owner_protocol_fee_component_proven',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'historical_protocol_fee_component_owned_by_current_owner_exact',
        )

    def test_snapshot_fast_path_supports_materialized_nonzero_prior_add_basis_fee_to_case_when_no_protocol_fee_lp_is_current(self):
        result = self._resolve(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'}},
                    'totalSupply': '12',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '10', 'amount0': '5', 'amount1': '10'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'basis_opens_current_round': False,
                    'current_round_trade_count_before_basis': 1,
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'exact_current_principal': {
                        'principal_amount_0_current': '5',
                        'principal_amount_1_current': '10',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 1,
                        'post_basis_remove_count': 0,
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 12,
                'last_trade_time_ms': 1100,
                'last_liquidity_event_time_ms': 1200,
                'fee_free_basis_transaction_id': 12,
                'fee_free_basis_time_ms': 1200,
                'fee_free_reserve_0': '6',
                'fee_free_reserve_1': '12',
                'fee_free_total_supply': '12',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '5')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '10')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            None,
        )
