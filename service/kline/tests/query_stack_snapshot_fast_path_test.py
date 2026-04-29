import sys
import unittest
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport


QueryStackTestSupport.install()


from query.read_models.position_metrics_snapshot_fast_path import PositionMetricsSnapshotFastPath  # noqa: E402
from query.read_models.position_metrics_snapshot_shadow_evaluator import PositionMetricsSnapshotShadowEvaluator  # noqa: E402


class QueryStackSnapshotFastPathTest(unittest.TestCase):
    def test_snapshot_fast_path_requires_strict_subset(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '14')
        self.assertEqual(result['live_metrics']['principal_amount1'], '21')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')

    def test_snapshot_fast_path_rejects_late_add_basis_when_position_opened_earlier(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '3.333333333333333334')
        self.assertEqual(result['live_metrics']['principal_amount1'], '7.5')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0.666666666666666666')
        self.assertEqual(result['live_metrics']['fee_amount1'], '1.5')
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
                'fee_to_account_at_basis': None,
                'fee_to_account_latest_known': None,
                'materialized_protocol_fee_split_case': None,
                'protocol_fee_split_semantic': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_profile': None,
                'unresolved_protocol_fee_semantic': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_explanation': None,
            },
        )

    def test_snapshot_fast_path_supports_swaps_after_opening_add_basis(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '3.333333333333333334')
        self.assertEqual(result['live_metrics']['principal_amount1'], '7.5')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0.666666666666666666')
        self.assertEqual(result['live_metrics']['fee_amount1'], '1.5')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_swaps')

    def test_snapshot_fast_path_supports_fee_to_opening_mint_without_post_basis_transactions(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10.000227293391365082',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '9.093389106119850868')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10.999999999999999999')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '0.002066820271473392')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '0.002500170477793219')
        self.assertTrue(result['live_metrics']['owner_is_fee_to'])
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_no_post_basis_transactions',
        )

    def test_snapshot_fast_path_rejects_fee_to_mint_case_when_prior_liquidity_is_non_zero(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10.000227293391365082',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
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
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '6.666666666666666667')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '1.333333333333333333')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertTrue(result['live_metrics']['owner_is_fee_to'])
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_swaps',
        )

    def test_snapshot_fast_path_supports_opening_add_after_prior_swaps_with_post_basis_swaps(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '44.129357936641051392')
        self.assertEqual(result['live_metrics']['principal_amount1'], '56.666249990808418013')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0.003894110474745511')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '0')
        self.assertFalse(result['live_metrics']['owner_is_fee_to'])
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_swaps')

    def test_snapshot_fast_path_supports_zero_liquidity_bootstrap_before_opening_add_basis(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10.000227293391365082',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_no_post_basis_transactions',
        )

    def test_snapshot_fast_path_supports_reopen_from_zero_before_current_round_basis(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '9.090909090909090909')
        self.assertEqual(result['live_metrics']['principal_amount1'], '11')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')

    def test_snapshot_fast_path_rejects_add_basis_when_prior_current_round_liquidity_is_non_zero(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
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
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '6.666666666666666667')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '1.333333333333333333')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_swaps',
        )

    def test_snapshot_fast_path_supports_zero_liquidity_bootstrap_opening_add_after_prior_swaps(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '44.129357936641051392')
        self.assertEqual(result['live_metrics']['principal_amount1'], '56.666249990808418013')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0.003894110474745511')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_swaps')

    def test_snapshot_shadow_evaluator_marks_structurally_aligned_non_exact_metrics_as_financially_pending(self):
        shadow = PositionMetricsSnapshotShadowEvaluator().evaluate(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'status': 'active',
                'current_liquidity': '7',
            },
            live_metrics={
                'metrics_status': 'partial',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'computation_blockers': ['missing_fee_growth_trace'],
                'value_warning_codes': ['estimated_values'],
            },
            liquidity_history=[{'transaction_id': 13, 'created_at': 1234, 'transaction_type': 'AddLiquidity'}],
            pool_transaction_history=[{'transaction_id': 13, 'created_at': 1234, 'transaction_type': 'AddLiquidity'}],
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
            ['exact_fee_not_supported', 'exact_principal_not_supported', 'missing_fee_growth_trace', 'estimated_values'],
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
                'fee_to_account_at_basis': None,
                'fee_to_account_latest_known': None,
                'materialized_protocol_fee_split_case': None,
                'protocol_fee_split_semantic': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_profile': None,
                'unresolved_protocol_fee_semantic': 'not_applicable_or_unknown',
                'unresolved_protocol_fee_explanation': None,
            },
        )

    def test_snapshot_fast_path_supports_latest_add_after_prior_current_round_liquidity_when_no_current_round_swaps_before_basis(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '14')
        self.assertEqual(result['live_metrics']['principal_amount1'], '21')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')

    def test_snapshot_fast_path_rejects_latest_add_after_prior_current_round_liquidity_when_current_round_had_swaps_before_basis(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '14')
        self.assertEqual(result['live_metrics']['principal_amount1'], '21')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_latest_remove_with_later_pool_liquidity_when_no_intervening_swaps(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '5')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(result['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_liquidity_changes')

    def test_snapshot_fast_path_rejects_later_pool_liquidity_when_intervening_swaps_exist(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '10')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '2')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes',
        )

    def test_snapshot_fast_path_supports_materialized_current_principal_for_intervening_swaps_before_later_adds(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '20')
        self.assertEqual(result['live_metrics']['fee_amount0'], '2')
        self.assertEqual(result['live_metrics']['fee_amount1'], '2')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['exact_current_principal_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_materialized_current_principal_with_post_basis_remove_when_fee_to_disabled(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '3')
        self.assertEqual(result['live_metrics']['principal_amount1'], '9')
        self.assertEqual(result['live_metrics']['fee_amount0'], '1')
        self.assertEqual(result['live_metrics']['fee_amount1'], '1')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_materialized_current_principal_with_post_basis_remove_when_fee_to_enabled_but_owner_is_not_fee_to(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '3')
        self.assertEqual(result['live_metrics']['principal_amount1'], '9')
        self.assertEqual(result['live_metrics']['fee_amount0'], '1')
        self.assertEqual(result['live_metrics']['fee_amount1'], '1')
        self.assertFalse(result['live_metrics']['owner_is_fee_to'])
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_fee_to_owner_materialized_current_principal_with_post_basis_remove_for_opening_add_basis(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertTrue(result['live_metrics']['owner_is_fee_to'])
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_snapshot_fast_path_supports_fee_to_owner_materialized_current_principal_with_latest_remove_basis(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertTrue(result['live_metrics']['owner_is_fee_to'])
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_latest_remove_basis',
        )

    def test_snapshot_fast_path_supports_fee_to_owner_materialized_current_principal_with_post_basis_remove_when_current_owner_protocol_fee_component_is_proven(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertTrue(result['live_metrics']['owner_is_fee_to'])
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'current_owner_protocol_fee_component_proven',
        )

    def test_snapshot_fast_path_rejects_materialized_nonzero_prior_add_basis_fee_to_case(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
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
                        'owner': 'chain-fee:0xfee-owner',
                        'continuity_case': 'unknown_missing_pre_basis_anchor',
                        'change_count_after_basis': 0,
                        'known_before_basis': False,
                        'fee_to_account_at_basis': None,
                        'fee_to_account_latest_known': 'chain-fee:0xfee-owner',
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
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
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
                        'owner': 'chain-fee:0xfee-owner',
                        'continuity_case': 'continuous_no_changes_after_basis',
                        'change_count_after_basis': 0,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': 'chain-fee:0xfee-owner',
                        'fee_to_account_latest_known': 'chain-fee:0xfee-owner',
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_continuous_nonzero_prior_add_basis',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'fee_to_continuous_nonzero_prior_add_exact',
        )

    def test_snapshot_fast_path_supports_materialized_nonzero_prior_add_basis_fee_to_case_when_basis_only_mint_is_proven(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
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
                        'owner': 'chain-fee:0xfee-owner',
                        'continuity_case': 'changed_after_basis',
                        'change_count_after_basis': 2,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': 'chain-fee:0xfee-owner',
                        'fee_to_account_latest_known': 'chain-fee:0xother-owner',
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_basis_only_nonzero_prior_add_basis',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'fee_to_basis_only_nonzero_prior_add_exact',
        )

    def test_snapshot_fast_path_supports_historical_protocol_fee_mints_owned_by_current_owner(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xother-owner'}},
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
                        'owner': 'chain-fee:0xfee-owner',
                        'continuity_case': 'changed_after_basis',
                        'change_count_after_basis': 1,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': 'chain-fee:0xfee-owner',
                        'fee_to_account_latest_known': 'chain-fee:0xother-owner',
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'all_protocol_fee_mints_owned_by_current_owner',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'historical_protocol_fee_mints_owned_by_current_owner_exact',
        )

    def test_snapshot_fast_path_supports_proven_current_owner_protocol_fee_component(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xother-owner'}},
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
                        'owner': 'chain-fee:0xfee-owner',
                        'continuity_case': 'changed_after_basis',
                        'change_count_after_basis': 2,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': 'chain-fee:0xfee-owner',
                        'fee_to_account_latest_known': 'chain-fee:0xother-owner',
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'current_owner_protocol_fee_component_proven',
        )
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['protocol_fee_split_semantic'],
            'historical_protocol_fee_component_owned_by_current_owner_exact',
        )

    def test_snapshot_fast_path_supports_materialized_nonzero_prior_add_basis_fee_to_case_when_no_protocol_fee_lp_is_live(self):
        result = PositionMetricsSnapshotFastPath().resolve(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            },
            payload={
                'data': {
                    'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
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
        self.assertEqual(result['live_metrics']['principal_amount0'], '5')
        self.assertEqual(result['live_metrics']['principal_amount1'], '10')
        self.assertEqual(result['live_metrics']['protocol_fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['protocol_fee_amount1'], '0')
        self.assertEqual(result['live_metrics']['fee_amount0'], '0')
        self.assertEqual(result['live_metrics']['fee_amount1'], '0')
        self.assertEqual(
            result['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            None,
        )

    def test_snapshot_shadow_evaluator_marks_unresolved_nonzero_prior_add_basis_fee_to_case(self):
        result = PositionMetricsSnapshotShadowEvaluator().evaluate(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'status': 'active',
                'current_liquidity': '10',
            },
            live_metrics={
                'metrics_status': 'partial_live_redeemable_only',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'position_liquidity_live': '12',
                'owner_is_fee_to': True,
                'computation_blockers': ['missing_protocol_fee_provenance'],
                'value_warning_codes': [],
            },
            liquidity_history=[
                {
                    'transaction_id': 10,
                    'created_at': 1000,
                    'transaction_type': 'AddLiquidity',
                }
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 12,
                    'created_at': 1200,
                    'transaction_type': 'RemoveLiquidity',
                }
            ],
            position_basis_snapshot={
                'status': 'active',
                'basis_type': 'add_liquidity',
                'current_liquidity': '10',
                'basis_transaction_id': 10,
                'basis_time_ms': 1000,
                'state_payload_json': {
                    'prior_liquidity_before_basis': '2',
                    'fee_to_continuity': {
                        'owner': 'chain-fee:0xfee-owner',
                        'continuity_case': 'changed_after_basis',
                        'change_count_after_basis': 1,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': 'chain-fee:0xfee-owner',
                        'fee_to_account_latest_known': 'chain-fee:0xother-owner',
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
                'exact_fee_not_supported',
                'exact_principal_not_supported',
                'missing_protocol_fee_provenance',
            ],
        )

    def test_snapshot_shadow_evaluator_marks_safe_continuous_nonzero_prior_add_basis_fee_to_case(self):
        result = PositionMetricsSnapshotShadowEvaluator().evaluate(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'status': 'active',
                'current_liquidity': '10',
            },
            live_metrics={
                'metrics_status': 'exact_no_swap_history',
                'exact_fee_supported': True,
                'exact_principal_supported': True,
                'position_liquidity_live': '12',
                'owner_is_fee_to': True,
                'computation_blockers': [],
                'value_warning_codes': [],
            },
            liquidity_history=[
                {
                    'transaction_id': 10,
                    'created_at': 1000,
                    'transaction_type': 'AddLiquidity',
                }
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 12,
                    'created_at': 1200,
                    'transaction_type': 'AddLiquidity',
                }
            ],
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
                        'owner': 'chain-fee:0xfee-owner',
                        'continuity_case': 'continuous_no_changes_after_basis',
                        'change_count_after_basis': 0,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': 'chain-fee:0xfee-owner',
                        'fee_to_account_latest_known': 'chain-fee:0xfee-owner',
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
        result = PositionMetricsSnapshotShadowEvaluator().evaluate(
            position={
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'status': 'active',
                'current_liquidity': '10',
            },
            live_metrics={
                'metrics_status': 'exact_no_swap_history',
                'exact_fee_supported': True,
                'exact_principal_supported': True,
                'position_liquidity_live': '12',
                'owner_is_fee_to': True,
                'computation_blockers': [],
                'value_warning_codes': [],
            },
            liquidity_history=[
                {
                    'transaction_id': 10,
                    'created_at': 1000,
                    'transaction_type': 'AddLiquidity',
                }
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 12,
                    'created_at': 1200,
                    'transaction_type': 'AddLiquidity',
                }
            ],
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
                        'owner': 'chain-fee:0xfee-owner',
                        'continuity_case': 'changed_after_basis',
                        'change_count_after_basis': 2,
                        'known_before_basis': True,
                        'fee_to_account_at_basis': 'chain-fee:0xfee-owner',
                        'fee_to_account_latest_known': 'chain-fee:0xother-owner',
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
