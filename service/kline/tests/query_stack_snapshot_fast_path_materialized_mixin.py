class QueryStackSnapshotFastPathMaterializedMixin:
    def test_snapshot_fast_path_supports_latest_add_after_prior_current_round_liquidity_when_no_current_round_swaps_before_basis(self):
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
                'basis_type': 'add_liquidity',
                'current_liquidity': '7',
                'basis_transaction_id': 15,
                'basis_time_ms': 2000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '5',
                    'basis_opens_current_round': False,
                    'has_only_zero_liquidity_before_basis': False,
                    'current_round_trade_count_before_basis': 0,
                    'current_round_liquidity_event_count': 2,
                    'current_round_started_at': 1000,
                    'current_round_started_transaction_id': 13,
                    'trade_count_between_basis_and_fee_free_basis': 0,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 15,
                'last_trade_time_ms': 900,
                'last_liquidity_event_time_ms': 2000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 2000,
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

    def test_snapshot_fast_path_rejects_latest_add_after_prior_current_round_liquidity_when_current_round_had_swaps_before_basis(self):
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
                'basis_type': 'add_liquidity',
                'current_liquidity': '7',
                'basis_transaction_id': 15,
                'basis_time_ms': 2000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '5',
                    'basis_opens_current_round': False,
                    'has_only_zero_liquidity_before_basis': False,
                    'current_round_trade_count_before_basis': 1,
                    'current_round_liquidity_event_count': 2,
                    'current_round_started_at': 1000,
                    'current_round_started_transaction_id': 13,
                    'trade_count_between_basis_and_fee_free_basis': 1,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 15,
                'last_trade_time_ms': 1500,
                'last_liquidity_event_time_ms': 2000,
                'fee_free_basis_transaction_id': 15,
                'fee_free_basis_time_ms': 2000,
                'fee_free_reserve_0': '14',
                'fee_free_reserve_1': '21',
                'fee_free_total_supply': '10',
            },
        )

        self.assertIsNone(result)

    def test_snapshot_fast_path_supports_latest_add_after_prior_current_round_swaps_when_materialized_current_principal_exists(self):
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
                'basis_type': 'add_liquidity',
                'current_liquidity': '7',
                'basis_transaction_id': 15,
                'basis_time_ms': 2000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '5',
                    'basis_opens_current_round': False,
                    'has_only_zero_liquidity_before_basis': False,
                    'current_round_trade_count_before_basis': 1,
                    'current_round_liquidity_event_count': 2,
                    'current_round_started_at': 1000,
                    'current_round_started_transaction_id': 13,
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'exact_current_principal': {
                        'principal_amount_0_current': '14',
                        'principal_amount_1_current': '21',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 1,
                        'post_basis_remove_count': 0,
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 16,
                'last_trade_time_ms': 1500,
                'last_liquidity_event_time_ms': 2000,
                'fee_free_basis_transaction_id': 16,
                'fee_free_basis_time_ms': 2100,
                'fee_free_reserve_0': '20',
                'fee_free_reserve_1': '30',
                'fee_free_total_supply': '10',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '14')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '21')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_latest_remove_with_later_pool_liquidity_when_no_intervening_swaps(self):
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
                    'totalSupply': '20',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '5', 'amount0': '5', 'amount1': '5'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'remove_liquidity',
                'current_liquidity': '5',
                'basis_transaction_id': 15,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'trade_count_between_basis_and_fee_free_basis': 0,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 16,
                'last_trade_time_ms': 900,
                'last_liquidity_event_time_ms': 1100,
                'fee_free_basis_transaction_id': 16,
                'fee_free_basis_time_ms': 1100,
                'fee_free_reserve_0': '20',
                'fee_free_reserve_1': '20',
                'fee_free_total_supply': '20',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['projected_metrics']['principal_amount0'], '5')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '5')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_liquidity_changes')

    def test_snapshot_fast_path_rejects_later_pool_liquidity_when_intervening_swaps_exist(self):
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
                    'totalSupply': '20',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '5', 'amount0': '5', 'amount1': '5'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'remove_liquidity',
                'current_liquidity': '5',
                'basis_transaction_id': 15,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'trade_count_between_basis_and_fee_free_basis': 1,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 16,
                'last_trade_time_ms': 1050,
                'last_liquidity_event_time_ms': 1100,
                'fee_free_basis_transaction_id': 16,
                'fee_free_basis_time_ms': 1100,
                'fee_free_reserve_0': '20',
                'fee_free_reserve_1': '20',
                'fee_free_total_supply': '20',
            },
        )

        self.assertIsNone(result)

    def test_snapshot_fast_path_supports_fee_to_opening_mint_with_later_pool_liquidity(self):
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
                    'totalSupply': '24',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '12', 'amount0': '12', 'amount1': '12'},
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
                    'trade_count_between_basis_and_fee_free_basis': 0,
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 16,
                'last_trade_time_ms': None,
                'last_liquidity_event_time_ms': 1100,
                'fee_free_basis_transaction_id': 16,
                'fee_free_basis_time_ms': 1100,
                'fee_free_reserve_0': '24',
                'fee_free_reserve_1': '24',
                'fee_free_total_supply': '24',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '10')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '10')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount0'], '2')
        self.assertEqual(result['projected_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '0')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes',
        )

    def test_snapshot_fast_path_supports_materialized_current_principal_for_intervening_swaps_before_later_adds(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '20',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '10', 'amount0': '7', 'amount1': '22'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'basis_opens_current_round': True,
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'exact_current_principal': {
                        'principal_amount_0_current': '5',
                        'principal_amount_1_current': '20',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 1,
                        'post_basis_remove_count': 0,
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 13,
                'last_trade_time_ms': 1300,
                'last_liquidity_event_time_ms': 1200,
                'fee_free_basis_transaction_id': 12,
                'fee_free_basis_time_ms': 1200,
                'fee_free_reserve_0': '11',
                'fee_free_reserve_1': '40',
                'fee_free_total_supply': '20',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '5')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '20')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '2')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '2')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['exact_current_principal_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_materialized_current_principal_with_post_basis_remove_when_fee_to_disabled(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': None},
                    'totalSupply': '9',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '10', 'amount0': '4', 'amount1': '10'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'remove_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'exact_current_principal': {
                        'principal_amount_0_current': '3',
                        'principal_amount_1_current': '9',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 0,
                        'post_basis_remove_count': 1,
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 12,
                'last_trade_time_ms': 1100,
                'last_liquidity_event_time_ms': 1200,
                'fee_free_basis_transaction_id': 12,
                'fee_free_basis_time_ms': 1200,
                'fee_free_reserve_0': '5',
                'fee_free_reserve_1': '18',
                'fee_free_total_supply': '9',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '3')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '9')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '1')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '1')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_materialized_current_principal_with_post_basis_remove_when_fee_to_enabled_but_owner_is_not_fee_to(self):
        result = self._resolve(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'}},
                    'totalSupply': '9',
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '10', 'amount0': '4', 'amount1': '10'},
                }
            },
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'remove_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'exact_current_principal': {
                        'principal_amount_0_current': '3',
                        'principal_amount_1_current': '9',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 0,
                        'post_basis_remove_count': 1,
                    },
                },
            },
            pool_state_snapshot={
                'last_transaction_id': 12,
                'last_trade_time_ms': 1100,
                'last_liquidity_event_time_ms': 1200,
                'fee_free_basis_transaction_id': 12,
                'fee_free_basis_time_ms': 1200,
                'fee_free_reserve_0': '5',
                'fee_free_reserve_1': '18',
                'fee_free_total_supply': '9',
            },
        )

        self.assertIsNotNone(result)
        self.assertEqual(result['projected_metrics']['principal_amount0'], '3')
        self.assertEqual(result['projected_metrics']['principal_amount1'], '9')
        self.assertEqual(result['projected_metrics']['fee_amount0'], '1')
        self.assertEqual(result['projected_metrics']['fee_amount1'], '1')
        self.assertFalse(result['projected_metrics']['owner_receives_protocol_fees'])
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_fee_to_owner_materialized_current_principal_with_post_basis_remove_for_opening_add_basis(self):
        result = self._resolve(
            position={
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
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
                    'prior_liquidity_before_basis': '0',
                    'basis_opens_current_round': True,
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'exact_current_principal': {
                        'principal_amount_0_current': '5',
                        'principal_amount_1_current': '10',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 0,
                        'post_basis_remove_count': 1,
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
        self.assertTrue(result['projected_metrics']['owner_receives_protocol_fees'])
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_fee_to_owner_materialized_current_principal_with_latest_remove_basis(self):
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
                'basis_type': 'remove_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'exact_current_principal': {
                        'principal_amount_0_current': '5',
                        'principal_amount_1_current': '10',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 0,
                        'post_basis_remove_count': 1,
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
        self.assertTrue(result['projected_metrics']['owner_receives_protocol_fees'])
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_latest_remove_basis',
        )

    def test_snapshot_fast_path_supports_fee_to_owner_materialized_current_principal_with_post_basis_remove_when_current_owner_protocol_fee_component_is_proven(self):
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
                'basis_type': 'remove_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'trade_count_between_basis_and_fee_free_basis': 1,
                    'exact_current_principal': {
                        'principal_amount_0_current': '5',
                        'principal_amount_1_current': '10',
                        'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                        'post_basis_add_count': 0,
                        'post_basis_remove_count': 1,
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
        self.assertTrue(result['projected_metrics']['owner_receives_protocol_fees'])
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'current_owner_protocol_fee_component_proven',
        )

