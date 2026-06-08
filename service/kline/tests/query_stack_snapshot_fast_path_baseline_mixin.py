class QueryStackSnapshotFastPathBaselineMixin:
    def test_snapshot_fast_path_uses_recorded_position_liquidity_when_snapshot_is_owner_level(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '6',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '100',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '6', 'amount0': '12', 'amount1': '18'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '36',
                'basis_transaction_id': 15,
                'basis_time_ms': 1000,
                'semantic_facts': {
                    'basis_opens_current_round': True,
                    'current_round_trade_count_before_basis': 0,
                    'exact_current_principal_case': 'materialized_current_principal',
                    'principal_amount_0_current': '10',
                    'principal_amount_1_current': '15',
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 16,
                'last_trade_time_ms': 1200,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 1000,
                'fee_free_reserve_0': '100',
                'fee_free_reserve_1': '150',
                'fee_free_total_supply': '100',
            },
        )

        self.assertIsNotNone(result)
        metrics = result['projected_metrics']
        self.assertEqual(metrics['position_liquidity'], '6')
        self.assertEqual(metrics['fee_calculation_complete'], True)
        self.assertEqual(metrics['value_warning_codes'], [])
        self.assertEqual(metrics['fee_amount0'], '6')
        self.assertEqual(metrics['fee_amount1'], '9')

    def test_snapshot_fast_path_requires_strict_subset(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '7',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '10',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '7', 'amount0': '14', 'amount1': '21'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'remove_liquidity',
                'current_liquidity': '7',
                'basis_transaction_id': 13,
                'basis_time_ms': 1000,
            },
            pool_state_snapshot={
                'last_transaction_id': 14,
                'last_trade_time_ms': None,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 1001,
                'fee_free_reserve_0': '14',
                'fee_free_reserve_1': '21',
                'fee_free_total_supply': '10',
            },
        )

        self.assertIsNone(result)

    def test_snapshot_fast_path_supports_latest_remove_liquidity_basis_without_later_transactions(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '7',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '10',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '7', 'amount0': '14', 'amount1': '21'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'remove_liquidity',
                'current_liquidity': '7',
                'basis_transaction_id': 15,
                'basis_time_ms': 1000,
            },
            pool_state_snapshot={
                'last_transaction_id': 15,
                'last_trade_time_ms': 950,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 1000,
                'fee_free_reserve_0': '14',
                'fee_free_reserve_1': '21',
                'fee_free_total_supply': '10',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '14')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '21')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')

    def test_snapshot_fast_path_rejects_late_add_basis_when_position_opened_earlier(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '7',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '10',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '7', 'amount0': '14', 'amount1': '21'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '7',
                'basis_transaction_id': 15,
                'basis_time_ms': 1000,
            },
            pool_state_snapshot={
                'last_transaction_id': 15,
                'last_trade_time_ms': None,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 1000,
                'fee_free_reserve_0': '14',
                'fee_free_reserve_1': '21',
                'fee_free_total_supply': '10',
            },
        )

        self.assertIsNone(result)

    def test_snapshot_fast_path_supports_swaps_after_latest_liquidity_basis(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '5',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '5',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '5', 'amount0': '4', 'amount1': '9'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'remove_liquidity',
                'current_liquidity': '5',
                'basis_transaction_id': 15,
                'basis_time_ms': 1000,
            },
            pool_state_snapshot={
                'last_transaction_id': 17,
                'last_trade_time_ms': 1200,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 1000,
                'fee_free_reserve_0': '3.333333333333333334',
                'fee_free_reserve_1': '7.5',
                'fee_free_total_supply': '5',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '3.333333333333333334')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '7.5')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0.666666666666666666')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '1.5')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_swaps')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot'],
            {
                'status': 'active',
                'basis_type': 'remove_liquidity',
                'current_liquidity': '5',
                'basis_transaction_id': 15,
                'basis_time_ms': 1000,
                'basis_opens_current_round': False,
                'has_only_zero_liquidity_before_basis': False,
                'current_round_liquidity_event_count': None,
                'current_round_started_at': None,
                'current_round_started_transaction_id': None,
                'current_round_trade_count_before_basis': None,
                'trade_count_between_basis_and_fee_free_basis': None,
                'exact_current_principal_case': None,
                'protocol_fee_liquidity_provenance_case': None,
                'basis_protocol_fee_liquidity_minted': None,
                'post_basis_protocol_fee_liquidity_minted': None,
                'post_basis_protocol_fee_mint_event_count': None,
                'post_basis_protocol_fee_liquidity_minted_before_first_add': None,
                'fee_to_continuous_protocol_fee_liquidity_current': None,
                'protocol_fee_current_owner_provenance_case': None,
                'basis_protocol_fee_liquidity_owned_by_current_owner': None,
                'post_basis_protocol_fee_liquidity_owned_by_current_owner': None,
                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': None,
                'protocol_fee_liquidity_owned_by_current_owner_current': None,
                'protocol_fee_liquidity_owned_by_other_accounts': None,
                'protocol_fee_liquidity_owner_unknown': None,
                'fee_to_continuity_case': None,
                'fee_to_continuity_change_count_after_basis': None,
                'fee_to_continuity_known_before_basis': None,
                'fee_to_continuity_owner': None,
                'fee_to_account_at_basis': None,
                'fee_to_account_latest_known': None,
                'materialized_protocol_fee_split_case': None,
                'protocol_fee_split_semantic': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_profile': None,
                'unresolved_protocol_fee_semantic': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_boundary_status': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_explanation': None,
            },
        )

    def test_snapshot_fast_path_supports_swaps_after_opening_add_basis(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '5',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '5',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '5', 'amount0': '4', 'amount1': '9'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '5',
                'basis_transaction_id': 15,
                'basis_time_ms': 1000,
            },
            pool_state_snapshot={
                'last_transaction_id': 17,
                'last_trade_time_ms': 1200,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 1000,
                'fee_free_reserve_0': '3.333333333333333334',
                'fee_free_reserve_1': '7.5',
                'fee_free_total_supply': '5',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '3.333333333333333334')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '7.5')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0.666666666666666666')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '1.5')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_swaps')

    def test_snapshot_fast_path_supports_fee_to_opening_mint_without_post_basis_transactions(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10.000227293391365082',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}},
                    'totalSupply': '110.002500227305015907',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '10.002500227305015907',
                        'amount0': '9.095455926391324260',
                        'amount1': '11.002500170477793218',
                    },
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10.000227293391365082',
                'basis_transaction_id': 3,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 3,
                'last_trade_time_ms': 900,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 3,
                'fee_free_basis_time_ms': 1000,
                'fee_free_reserve_0': '100',
                'fee_free_reserve_1': '121',
                'fee_free_total_supply': '110',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '9.093389106119850868')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '10.999999999999999999')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '0.002066820271473392')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '0.002500170477793219')
        self.assertTrue(result['projected_metrics']['owner_receives_protocol_fees'])
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_no_post_basis_transactions',
        )

    def test_snapshot_fast_path_rejects_fee_to_mint_case_when_prior_liquidity_is_non_zero(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10.000227293391365082',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}},
                    'totalSupply': '110.002500227305015907',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '10.002500227305015907',
                        'amount0': '9.095455926391324260',
                        'amount1': '11.002500170477793218',
                    },
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10.000227293391365082',
                'basis_transaction_id': 3,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '1',
                    'basis_opens_current_round': False,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 3,
                'last_trade_time_ms': 900,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 3,
                'fee_free_basis_time_ms': 1000,
                'fee_free_reserve_0': '100',
                'fee_free_reserve_1': '121',
                'fee_free_total_supply': '110',
            },
        )

        self.assertIsNone(result)

    def test_snapshot_fast_path_supports_fee_to_opening_mint_with_post_basis_swaps(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}},
                    'totalSupply': '120',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '12',
                        'amount0': '8',
                        'amount1': '12',
                    },
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 15,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 20,
                'last_trade_time_ms': 1300,
                'last_liquidity_event_time_ms': 1000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 1000,
                'fee_free_reserve_0': '80',
                'fee_free_reserve_1': '120',
                'fee_free_total_supply': '120',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '6.666666666666666667')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '10')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '1.333333333333333333')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '2')
        self.assertTrue(result['projected_metrics']['owner_receives_protocol_fees'])
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_swaps',
        )

    def test_snapshot_fast_path_supports_opening_add_after_prior_swaps_with_post_basis_swaps(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1_800_000_002_000,
                'status': 'active',
                'current_liquidity': '50.001136466956825411',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '150.004512399557745466',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '50.001136466956825411',
                        'amount0': '44.133252047115796903',
                        'amount1': '56.666249990808418012',
                    },
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '50.001136466956825411',
                'basis_transaction_id': 3,
                'basis_time_ms': 1_800_000_002_000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 4,
                'last_trade_time_ms': 1_800_000_003_000,
                'last_liquidity_event_time_ms': 1_800_000_002_000,
                'fee_free_basis_transaction_id': 3,
                'fee_free_basis_time_ms': 1_800_000_002_000,
                'fee_free_reserve_0': '132.389047280274299409',
                'fee_free_reserve_1': '170',
                'fee_free_total_supply': '150.004512399557745466',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '44.129357936641051392')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '56.666249990808418013')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0.003894110474745511')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '0')
        self.assertFalse(result['projected_metrics']['owner_receives_protocol_fees'])
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_swaps')

    def test_snapshot_fast_path_supports_zero_liquidity_bootstrap_before_opening_add_basis(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10.000227293391365082',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}},
                    'totalSupply': '110.002500227305015907',
                    'virtualInitialLiquidity': True,
                    'liquidity': {
                        'liquidity': '10.002500227305015907',
                        'amount0': '9.095455926391324260',
                        'amount1': '11.002500170477793218',
                    },
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10.000227293391365082',
                'basis_transaction_id': 3,
                'basis_time_ms': 1_800_000_001_000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                    'has_only_zero_liquidity_before_basis': True,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 3,
                'last_trade_time_ms': 900,
                'last_liquidity_event_time_ms': 1_800_000_001_000,
                'fee_free_basis_transaction_id': 3,
                'fee_free_basis_time_ms': 1_800_000_001_000,
                'fee_free_reserve_0': '100',
                'fee_free_reserve_1': '121',
                'fee_free_total_supply': '110',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_no_post_basis_transactions',
        )

    def test_snapshot_fast_path_supports_reopen_from_zero_before_current_round_basis(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}},
                    'totalSupply': '110.002500227305015907',
                    'virtualInitialLiquidity': True,
                    'liquidity': {
                        'liquidity': '10',
                        'amount0': '9.090909090909090909',
                        'amount1': '11',
                    },
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 3,
                'basis_time_ms': 1_800_000_001_000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                    'has_only_zero_liquidity_before_basis': False,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 3,
                'last_trade_time_ms': 900,
                'last_liquidity_event_time_ms': 1_800_000_001_000,
                'fee_free_basis_transaction_id': 3,
                'fee_free_basis_time_ms': 1_800_000_001_000,
                'fee_free_reserve_0': '100',
                'fee_free_reserve_1': '121.0',
                'fee_free_total_supply': '110.0',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '9.090909090909090909')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '11')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')

    def test_snapshot_fast_path_rejects_add_basis_when_prior_current_round_liquidity_is_non_zero(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '110',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '10',
                        'amount0': '9.090909090909090909',
                        'amount1': '11',
                    },
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 3,
                'basis_time_ms': 1_800_000_001_000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '1',
                    'basis_opens_current_round': False,
                    'has_only_zero_liquidity_before_basis': False,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 3,
                'last_trade_time_ms': 900,
                'last_liquidity_event_time_ms': 1_800_000_001_000,
                'fee_free_basis_transaction_id': 3,
                'fee_free_basis_time_ms': 1_800_000_001_000,
                'fee_free_reserve_0': '100',
                'fee_free_reserve_1': '121',
                'fee_free_total_supply': '110',
            },
        )

        self.assertIsNone(result)

    def test_snapshot_fast_path_supports_zero_liquidity_bootstrap_with_post_basis_swaps(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'}},
                    'totalSupply': '120',
                    'virtualInitialLiquidity': True,
                    'liquidity': {
                        'liquidity': '12',
                        'amount0': '8',
                        'amount1': '12',
                    },
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 15,
                'basis_time_ms': 1_800_000_001_000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                    'has_only_zero_liquidity_before_basis': True,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 20,
                'last_trade_time_ms': 1_800_000_001_300,
                'last_liquidity_event_time_ms': 1_800_000_001_000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 1_800_000_001_000,
                'fee_free_reserve_0': '80',
                'fee_free_reserve_1': '120',
                'fee_free_total_supply': '120',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '6.666666666666666667')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '10')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '1.333333333333333333')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_swaps',
        )

    def test_snapshot_fast_path_supports_zero_liquidity_bootstrap_opening_add_after_prior_swaps(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '50.001136466956825411',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '150.004512399557745466',
                    'virtualInitialLiquidity': True,
                    'liquidity': {
                        'liquidity': '50.001136466956825411',
                        'amount0': '44.133252047115796903',
                        'amount1': '56.666249990808418012',
                    },
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '50.001136466956825411',
                'basis_transaction_id': 3,
                'basis_time_ms': 1_800_000_002_000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                    'has_only_zero_liquidity_before_basis': True,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 4,
                'last_trade_time_ms': 1_800_000_003_000,
                'last_liquidity_event_time_ms': 1_800_000_002_000,
                'fee_free_basis_transaction_id': 3,
                'fee_free_basis_time_ms': 1_800_000_002_000,
                'fee_free_reserve_0': '132.389047280274299409',
                'fee_free_reserve_1': '170',
                'fee_free_total_supply': '150.004512399557745466',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '44.129357936641051392')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '56.666249990808418013')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0.003894110474745511')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_swaps')

    def test_snapshot_shadow_evaluator_marks_structurally_aligned_non_exact_metrics_as_financially_pending(self):
        shadow = self._evaluate(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'status': 'active',
                'current_liquidity': '7',
            },
            projected_metrics={
                'metrics_status': 'partial',
                'fee_calculation_complete': False,
                'principal_calculation_complete': False,
                'computation_blockers': ['missing_fee_growth_trace'],
                'value_warning_codes': ['estimated_values'],
            },
            replay_summary={
                'latest_position_transaction_id': 13,
                'latest_position_created_at': 1234,
                'latest_pool_transaction_id': 13,
                'latest_pool_trade_time_ms': None,
                'latest_pool_liquidity_event_time_ms': 1234,
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '7',
                'basis_transaction_id': 13,
                'basis_time_ms': 1234,
                'state_payload_json': {
                    'basis_opens_current_round': True,
                    'has_only_zero_liquidity_before_basis': False,
                },
            },
            pool_state_snapshot={'last_transaction_id': 13, 'last_trade_time_ms': None, 'last_liquidity_event_time_ms': 1234},
        )

        self.assertEqual(shadow['snapshot_shadow']['mismatch_codes'], [])
        self.assertEqual(shadow['snapshot_shadow']['readiness'], 'financial_semantics_pending')
        self.assertEqual(
            shadow['snapshot_shadow']['readiness_reason_codes'],
            ['fee_calculation_incomplete', 'principal_calculation_incomplete', 'missing_fee_growth_trace', 'estimated_values'],
        )
        self.assertEqual(
            shadow['snapshot_shadow']['position_basis_snapshot'],
            {
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '7',
                'basis_transaction_id': 13,
                'basis_time_ms': 1234,
                'basis_opens_current_round': True,
                'has_only_zero_liquidity_before_basis': False,
                'current_round_liquidity_event_count': None,
                'current_round_started_at': None,
                'current_round_started_transaction_id': None,
                'current_round_trade_count_before_basis': None,
                'trade_count_between_basis_and_fee_free_basis': None,
                'exact_current_principal_case': None,
                'protocol_fee_liquidity_provenance_case': None,
                'basis_protocol_fee_liquidity_minted': None,
                'post_basis_protocol_fee_liquidity_minted': None,
                'post_basis_protocol_fee_mint_event_count': None,
                'post_basis_protocol_fee_liquidity_minted_before_first_add': None,
                'fee_to_continuous_protocol_fee_liquidity_current': None,
                'protocol_fee_current_owner_provenance_case': None,
                'basis_protocol_fee_liquidity_owned_by_current_owner': None,
                'post_basis_protocol_fee_liquidity_owned_by_current_owner': None,
                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': None,
                'protocol_fee_liquidity_owned_by_current_owner_current': None,
                'protocol_fee_liquidity_owned_by_other_accounts': None,
                'protocol_fee_liquidity_owner_unknown': None,
                'fee_to_continuity_case': None,
                'fee_to_continuity_change_count_after_basis': None,
                'fee_to_continuity_known_before_basis': None,
                'fee_to_continuity_owner': None,
                'fee_to_account_at_basis': None,
                'fee_to_account_latest_known': None,
                'materialized_protocol_fee_split_case': None,
                'protocol_fee_split_semantic': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_profile': None,
                'unresolved_protocol_fee_semantic': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_boundary_status': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_explanation': None,
            },
        )

