import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.position_metrics_snapshot_builder import PositionMetricsSnapshotBuilder  # noqa: E402
from market.settled_output_batch_factory import SettledOutputBatchFactory  # noqa: E402


class PositionMetricsSnapshotBuilderTest(unittest.TestCase):
    class FakeSnapshotSourceRepository:
        def __init__(self):
            self.pool_transaction_history = {}
            self.position_liquidity_history = {}
            self.pool_fee_to_history = {}
            self.pool_created_metadata = {}

        def list_pool_transaction_history(self, *, pool_application_id, pool_chain_id=None):
            self.last_pool_history_request = {
                'pool_application_id': pool_application_id,
                'pool_chain_id': pool_chain_id,
            }
            return list(self.pool_transaction_history.get(pool_application_id, []))

        def list_position_liquidity_history(self, *, owner, pool_application_id):
            return list(self.position_liquidity_history.get((owner, pool_application_id), []))

        def list_pool_fee_to_history(self, *, pool_application_id):
            return list(self.pool_fee_to_history.get(pool_application_id, []))

        def get_pool_created_metadata(self, *, pool_application_id):
            payload = self.pool_created_metadata.get(pool_application_id)
            if payload is None:
                return None
            return dict(payload)

    @staticmethod
    def _build_output_batch(outputs):
        return SettledOutputBatchFactory().build(outputs)

    def test_build_materialization_plan_rebuilds_pool_and_closed_position_snapshots(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '0',
                'created_at': 1000,
                'from_account': owner,
            },
            {
                'transaction_id': 11,
                'transaction_type': 'RemoveLiquidity',
                'amount_0_in': None,
                'amount_0_out': '2',
                'amount_1_in': None,
                'amount_1_out': '4',
                'liquidity': '3',
                'created_at': 2000,
                'from_account': owner,
            },
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = list(
            [
                row
                for row in source_repository.pool_transaction_history[pool_application_id]
                if row.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}
            ]
        )
        builder = PositionMetricsSnapshotBuilder(
            snapshot_materialization_inputs_repository=source_repository,
            settled_output_batch_factory=SettledOutputBatchFactory(),
        )

        plan = builder.build_materialization_plan(
            self._build_output_batch(
                [
                    {
                        'settled_output_type': 'settled_liquidity_change',
                        'pool_application_id': pool_application_id,
                        'pool_chain_id': 'chain-a',
                        'owner': settled_owner,
                    }
                ]
            )
        )

        self.assertEqual(plan['affected_pool_count'], 1)
        self.assertEqual(plan['affected_position_count'], 1)
        self.assertEqual(len(plan['pool_states']), 1)
        self.assertEqual(len(plan['position_replacements']), 1)
        pool_state = plan['pool_states'][0]
        self.assertEqual(pool_state['pool_state_id'], pool_application_id)
        self.assertEqual(pool_state['live_reserve_0'], '2')
        self.assertEqual(pool_state['live_reserve_1'], '5')
        self.assertEqual(pool_state['live_total_supply'], '3')
        self.assertEqual(pool_state['fee_free_basis_transaction_id'], 11)
        self.assertEqual(pool_state['fee_free_basis_time_ms'], 2000)
        self.assertEqual(pool_state['fee_free_reserve_0'], '2')
        self.assertEqual(pool_state['fee_free_reserve_1'], '5')
        self.assertEqual(pool_state['fee_free_total_supply'], '3')
        self.assertEqual(pool_state['last_liquidity_event_time_ms'], 2000)
        self.assertIsNone(pool_state['state_payload_json']['pool_created_metadata'])
        replacement = plan['position_replacements'][0]
        self.assertEqual(replacement['owner'], owner)
        self.assertEqual(replacement['pool_application_id'], pool_application_id)
        self.assertEqual(len(replacement['states']), 1)
        position_state = replacement['states'][0]
        self.assertEqual(position_state['status'], 'closed')
        self.assertEqual(position_state['current_liquidity'], '0')
        self.assertEqual(position_state['basis_type'], 'remove_liquidity')
        self.assertEqual(position_state['basis_amount_0'], '2')
        self.assertEqual(position_state['basis_amount_1'], '4')
        self.assertEqual(position_state['state_payload_json']['prior_liquidity_before_basis'], '0')
        self.assertEqual(position_state['state_payload_json']['current_round_liquidity_event_count'], 1)
        self.assertEqual(position_state['state_payload_json']['current_round_started_at'], 2000)
        self.assertEqual(position_state['state_payload_json']['current_round_started_transaction_id'], 11)

    def test_build_materialization_plan_ignores_trade_only_position_rebuilds(self):
        source_repository = self.FakeSnapshotSourceRepository()
        builder = PositionMetricsSnapshotBuilder(
            snapshot_materialization_inputs_repository=source_repository,
            settled_output_batch_factory=SettledOutputBatchFactory(),
        )

        plan = builder.build_materialization_plan(
            self._build_output_batch(
                [
                    {
                        'settled_output_type': 'settled_trade',
                        'pool_application_id': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a',
                        'pool_chain_id': 'chain-a',
                    }
                ]
            )
        )

        self.assertEqual(plan['affected_pool_count'], 1)
        self.assertEqual(plan['affected_position_count'], 0)
        self.assertEqual(plan['position_replacements'], [])

    def test_build_materialization_plan_persists_recorded_state_when_exact_swap_replay_is_blocked(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '1000',
                'amount_0_out': None,
                'amount_1_in': '1000',
                'amount_1_out': None,
                'liquidity': '0',
                'created_at': 1000,
                'from_account': owner,
            },
            {
                'transaction_id': 11,
                'transaction_type': 'BuyToken0',
                'amount_0_in': None,
                'amount_0_out': '2',
                'amount_1_in': '1',
                'amount_1_out': None,
                'liquidity': None,
                'created_at': 2000,
                'from_account': owner,
            },
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = [
            source_repository.pool_transaction_history[pool_application_id][0]
        ]
        builder = PositionMetricsSnapshotBuilder(
            snapshot_materialization_inputs_repository=source_repository,
            settled_output_batch_factory=SettledOutputBatchFactory(),
        )

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ])
        )

        self.assertEqual(len(plan['pool_states']), 1)
        pool_state = plan['pool_states'][0]
        self.assertEqual(pool_state['live_reserve_0'], '998')
        self.assertEqual(pool_state['live_reserve_1'], '1001')
        self.assertEqual(
            pool_state['state_payload_json']['exact_replay_blockers'],
            ['pool_history_contains_invalid_swap_amounts'],
        )
        replacement = plan['position_replacements'][0]
        self.assertEqual(len(replacement['states']), 1)
        self.assertEqual(replacement['states'][0]['current_liquidity'], '0')

    def test_build_materialization_plan_tracks_fee_free_state_from_latest_liquidity_basis(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '10',
                'amount_0_out': None,
                'amount_1_in': '10',
                'amount_1_out': None,
                'liquidity': '10',
                'created_at': 1000,
                'from_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user',
            },
            {
                'transaction_id': 11,
                'transaction_type': 'RemoveLiquidity',
                'amount_0_in': None,
                'amount_0_out': '5',
                'amount_1_in': None,
                'amount_1_out': '5',
                'liquidity': '5',
                'created_at': 2000,
                'from_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user',
            },
        ]
        source_repository.pool_transaction_history[pool_application_id].extend([
            {
                'transaction_id': 12,
                'transaction_type': 'BuyToken0',
                'amount_0_in': None,
                'amount_0_out': '1.663329996663329997',
                'amount_1_in': '2.5',
                'amount_1_out': None,
                'liquidity': None,
                'created_at': 3000,
                'from_account': 'chain-user:trader',
            }
        ])
        builder = PositionMetricsSnapshotBuilder(
            snapshot_materialization_inputs_repository=source_repository,
            settled_output_batch_factory=SettledOutputBatchFactory(),
        )

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_trade',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                }
            ]
            )
        )

        pool_state = plan['pool_states'][0]
        self.assertEqual(pool_state['last_transaction_id'], 12)
        self.assertEqual(pool_state['last_liquidity_event_time_ms'], 2000)
        self.assertEqual(pool_state['last_trade_time_ms'], 3000)
        self.assertEqual(pool_state['fee_free_basis_transaction_id'], 11)
        self.assertEqual(pool_state['fee_free_basis_time_ms'], 2000)
        self.assertEqual(pool_state['fee_free_reserve_0'], '3.333333333333333334')
        self.assertEqual(pool_state['fee_free_reserve_1'], '7.5')
        self.assertEqual(pool_state['fee_free_total_supply'], '5')
        self.assertEqual(pool_state['live_reserve_0'], '3.336670003336670003')
        self.assertEqual(pool_state['live_reserve_1'], '7.5')
        self.assertEqual(
            source_repository.last_pool_history_request,
            {'pool_application_id': pool_application_id, 'pool_chain_id': 'chain-a'},
        )

    def test_build_materialization_plan_persists_pool_created_metadata_into_pool_state_payload(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '0',
                'created_at': 1000,
                'from_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user',
            },
        ]
        source_repository.pool_created_metadata[pool_application_id] = {
            'event_family': 'swap_pool_created_recorded',
            'pool_application': pool_application_id,
            'token_0': 'token-a',
            'token_1': 'TLINERA',
        }
        builder = PositionMetricsSnapshotBuilder(
            snapshot_materialization_inputs_repository=source_repository,
            settled_output_batch_factory=SettledOutputBatchFactory(),
        )

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_trade',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                }
            ])
        )

        pool_state = plan['pool_states'][0]
        self.assertEqual(
            pool_state['state_payload_json']['pool_created_metadata'],
            {
                'event_family': 'swap_pool_created_recorded',
                'pool_application': pool_application_id,
                'token_0': 'token-a',
                'token_1': 'TLINERA',
            },
        )

    def test_build_materialization_plan_records_prior_liquidity_before_latest_basis(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '4',
                'created_at': 1000,
                'from_account': owner,
            },
            {
                'transaction_id': 11,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '2',
                'amount_0_out': None,
                'amount_1_in': '3',
                'amount_1_out': None,
                'liquidity': '2',
                'created_at': 2000,
                'from_account': owner,
            },
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = list(
            [
                row
                for row in source_repository.pool_transaction_history[pool_application_id]
                if row.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}
            ]
        )
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ]
            )
        )

        position_state = plan['position_replacements'][0]['states'][0]
        self.assertEqual(position_state['current_liquidity'], '6')
        self.assertEqual(position_state['state_payload_json']['prior_liquidity_before_basis'], '4')
        self.assertFalse(position_state['state_payload_json']['basis_opens_current_round'])
        self.assertFalse(position_state['state_payload_json']['has_only_zero_liquidity_before_basis'])
        self.assertEqual(position_state['state_payload_json']['current_round_liquidity_event_count'], 2)
        self.assertEqual(position_state['state_payload_json']['current_round_started_at'], 1000)
        self.assertEqual(position_state['state_payload_json']['current_round_started_transaction_id'], 10)
        self.assertEqual(position_state['state_payload_json']['current_round_trade_count_before_basis'], 0)
        self.assertEqual(position_state['state_payload_json']['trade_count_between_basis_and_fee_free_basis'], 0)

    def test_build_materialization_plan_persists_protocol_fee_liquidity_provenance(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '6',
                'created_at': 1000,
                'from_account': owner,
            },
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = list(
            [
                row
                for row in source_repository.pool_transaction_history[pool_application_id]
                if row.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}
            ]
        )
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        class FakePrincipalSimulator:
            def simulate_current_principal(self, **_kwargs):
                return {
                    'principal_amount_0_current': '3',
                    'principal_amount_1_current': '7',
                    'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                    'basis_protocol_fee_liquidity_minted': '5',
                    'post_basis_protocol_fee_liquidity_minted': '10',
                    'post_basis_protocol_fee_mint_event_count': 2,
                    'post_basis_protocol_fee_liquidity_minted_before_first_add': '7',
                    'fee_to_continuous_protocol_fee_liquidity_current': '15',
                    'protocol_fee_liquidity_provenance_case': 'basis_and_post_basis_mints',
                }

        class FakeProtocolFeeOwnershipTracker:
            def summarize(self, **_kwargs):
                return {
                    'basis_protocol_fee_liquidity_owned_by_current_owner': '5',
                    'post_basis_protocol_fee_liquidity_owned_by_current_owner': '10',
                    'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '7',
                    'protocol_fee_liquidity_owned_by_current_owner_current': '15',
                    'protocol_fee_liquidity_owned_by_other_accounts': '0',
                    'protocol_fee_liquidity_owner_unknown': '0',
                    'protocol_fee_current_owner_provenance_case': 'all_mints_owned_by_current_owner',
                }

        builder.principal_simulator = FakePrincipalSimulator()
        builder.protocol_fee_ownership_tracker = FakeProtocolFeeOwnershipTracker()

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ]
            )
        )

        exact_current_principal = plan['position_replacements'][0]['states'][0]['state_payload_json']['exact_current_principal']
        self.assertEqual(exact_current_principal['basis_protocol_fee_liquidity_minted'], '5')
        self.assertEqual(exact_current_principal['post_basis_protocol_fee_liquidity_minted'], '10')
        self.assertEqual(exact_current_principal['post_basis_protocol_fee_mint_event_count'], 2)
        self.assertEqual(exact_current_principal['post_basis_protocol_fee_liquidity_minted_before_first_add'], '7')
        self.assertEqual(exact_current_principal['fee_to_continuous_protocol_fee_liquidity_current'], '15')
        self.assertEqual(exact_current_principal['protocol_fee_liquidity_provenance_case'], 'basis_and_post_basis_mints')
        self.assertEqual(exact_current_principal['basis_protocol_fee_liquidity_owned_by_current_owner'], '5')
        self.assertEqual(exact_current_principal['post_basis_protocol_fee_liquidity_owned_by_current_owner'], '10')
        self.assertEqual(
            exact_current_principal['post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add'],
            '7',
        )
        self.assertEqual(exact_current_principal['protocol_fee_liquidity_owned_by_current_owner_current'], '15')
        self.assertEqual(exact_current_principal['protocol_fee_liquidity_owned_by_other_accounts'], '0')
        self.assertEqual(exact_current_principal['protocol_fee_liquidity_owner_unknown'], '0')
        self.assertEqual(
            exact_current_principal['protocol_fee_current_owner_provenance_case'],
            'all_mints_owned_by_current_owner',
        )

    def test_build_materialization_plan_marks_zero_liquidity_bootstrap_before_basis(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '0',
                'created_at': 1000,
                'from_account': owner,
            },
            {
                'transaction_id': 11,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '2',
                'amount_0_out': None,
                'amount_1_in': '3',
                'amount_1_out': None,
                'liquidity': '2',
                'created_at': 2000,
                'from_account': owner,
            },
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = list(
            source_repository.pool_transaction_history[pool_application_id]
        )
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ]
            )
        )

        position_state = plan['position_replacements'][0]['states'][0]
        self.assertEqual(position_state['current_liquidity'], '2')
        self.assertEqual(position_state['state_payload_json']['prior_liquidity_before_basis'], '0')
        self.assertTrue(position_state['state_payload_json']['basis_opens_current_round'])
        self.assertTrue(position_state['state_payload_json']['has_only_zero_liquidity_before_basis'])
        self.assertEqual(position_state['state_payload_json']['current_round_liquidity_event_count'], 1)
        self.assertEqual(position_state['state_payload_json']['current_round_started_at'], 2000)
        self.assertEqual(position_state['state_payload_json']['current_round_started_transaction_id'], 11)
        self.assertEqual(position_state['state_payload_json']['current_round_trade_count_before_basis'], 0)

    def test_build_materialization_plan_marks_reopen_from_zero_before_basis(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '4',
                'created_at': 1000,
                'from_account': owner,
            },
            {
                'transaction_id': 11,
                'transaction_type': 'RemoveLiquidity',
                'amount_0_in': None,
                'amount_0_out': '4',
                'amount_1_in': None,
                'amount_1_out': '9',
                'liquidity': '4',
                'created_at': 1500,
                'from_account': owner,
            },
            {
                'transaction_id': 12,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '2',
                'amount_0_out': None,
                'amount_1_in': '3',
                'amount_1_out': None,
                'liquidity': '2',
                'created_at': 2000,
                'from_account': owner,
            },
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = list(
            source_repository.pool_transaction_history[pool_application_id]
        )
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ]
            )
        )

        position_state = plan['position_replacements'][0]['states'][0]
        self.assertEqual(position_state['current_liquidity'], '2')
        self.assertEqual(position_state['state_payload_json']['prior_liquidity_before_basis'], '0')
        self.assertTrue(position_state['state_payload_json']['basis_opens_current_round'])
        self.assertFalse(position_state['state_payload_json']['has_only_zero_liquidity_before_basis'])
        self.assertEqual(position_state['state_payload_json']['current_round_liquidity_event_count'], 1)
        self.assertEqual(position_state['state_payload_json']['current_round_started_at'], 2000)
        self.assertEqual(position_state['state_payload_json']['current_round_started_transaction_id'], 12)
        self.assertEqual(position_state['state_payload_json']['current_round_trade_count_before_basis'], 0)

    def test_build_materialization_plan_counts_current_round_trades_before_basis(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '4',
                'created_at': 1000,
                'from_account': owner,
            },
            {
                'transaction_id': 11,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '2',
                'amount_0_out': None,
                'amount_1_in': '3',
                'amount_1_out': None,
                'liquidity': '2',
                'created_at': 2000,
                'from_account': owner,
            },
        ]
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '4',
                'created_at': 1000,
                'from_account': owner,
            },
            {
                'transaction_id': 11,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '2',
                'amount_0_out': None,
                'amount_1_in': '3',
                'amount_1_out': None,
                'liquidity': '2',
                'created_at': 2000,
                'from_account': owner,
            },
            {
                'transaction_id': 9,
                'transaction_type': 'BuyToken0',
                'amount_0_in': None,
                'amount_0_out': '1',
                'amount_1_in': '2',
                'amount_1_out': None,
                'liquidity': None,
                'created_at': 900,
                'from_account': 'chain-user:trader-a',
            },
            {
                'transaction_id': 10,
                'transaction_type': 'BuyToken0',
                'amount_0_in': None,
                'amount_0_out': '1',
                'amount_1_in': '2',
                'amount_1_out': None,
                'liquidity': None,
                'created_at': 1500,
                'from_account': 'chain-user:trader-b',
            },
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = list(
            [
                row
                for row in source_repository.pool_transaction_history[pool_application_id]
                if row.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}
            ]
        )
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ]
            )
        )

        position_state = plan['position_replacements'][0]['states'][0]
        self.assertEqual(position_state['state_payload_json']['current_round_trade_count_before_basis'], 1)
        self.assertEqual(position_state['state_payload_json']['trade_count_between_basis_and_fee_free_basis'], 0)

    def test_build_materialization_plan_counts_trades_between_basis_and_fee_free_basis(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '4',
                'created_at': 1000,
                'from_account': owner,
            },
            {
                'transaction_id': 12,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '2',
                'amount_0_out': None,
                'amount_1_in': '3',
                'amount_1_out': None,
                'liquidity': '2',
                'created_at': 2000,
                'from_account': 'chain-user:owner-b',
            },
            {
                'transaction_id': 11,
                'transaction_type': 'BuyToken0',
                'amount_0_in': None,
                'amount_0_out': '1',
                'amount_1_in': '2',
                'amount_1_out': None,
                'liquidity': None,
                'created_at': 1500,
                'from_account': 'chain-user:trader-a',
            },
            {
                'transaction_id': 13,
                'transaction_type': 'SellToken0',
                'amount_0_in': '1',
                'amount_0_out': None,
                'amount_1_in': None,
                'amount_1_out': '1',
                'liquidity': None,
                'created_at': 2500,
                'from_account': 'chain-user:trader-b',
            },
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = [
            row
            for row in source_repository.pool_transaction_history[pool_application_id]
            if row.get('from_account') == owner and row.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}
        ]
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ]
            )
        )

        position_state = plan['position_replacements'][0]['states'][0]
        self.assertEqual(position_state['state_payload_json']['trade_count_between_basis_and_fee_free_basis'], 1)

    def test_build_materialization_plan_persists_exact_current_principal_payload(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '6',
                'created_at': 1000,
                'from_account': owner,
            },
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = list(
            source_repository.pool_transaction_history[pool_application_id]
        )
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        class FakePrincipalSimulator:
            def simulate_current_principal(self, **_kwargs):
                return {
                    'principal_amount_0_current': '3',
                    'principal_amount_1_current': '7',
                    'exact_current_principal_case': 'post_basis_swaps_without_liquidity_changes',
                }

        class FakeProtocolFeeOwnershipTracker:
            def summarize(self, **_kwargs):
                return None

        builder.principal_simulator = FakePrincipalSimulator()
        builder.protocol_fee_ownership_tracker = FakeProtocolFeeOwnershipTracker()

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ]
            )
        )

        position_state = plan['position_replacements'][0]['states'][0]
        self.assertEqual(
            position_state['state_payload_json']['exact_current_principal'],
            {
                'principal_amount_0_current': '3',
                'principal_amount_1_current': '7',
                'exact_current_principal_case': 'post_basis_swaps_without_liquidity_changes',
            },
        )

    def test_build_materialization_plan_persists_fee_to_continuity_payload(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '6',
                'created_at': 1000,
                'from_account': owner,
            }
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = list(
            source_repository.pool_transaction_history[pool_application_id]
        )
        source_repository.pool_fee_to_history[pool_application_id] = [
            {
                'transaction_id': 9,
                'created_at': 900,
                'fee_to_account': 'chain-fee:0xfee-owner',
            }
        ]
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ]
            )
        )

        continuity = plan['position_replacements'][0]['states'][0]['state_payload_json']['fee_to_continuity']
        self.assertEqual(continuity['continuity_case'], 'continuous_no_changes_after_basis')
        self.assertEqual(continuity['change_count_after_basis'], 0)
        self.assertTrue(continuity['known_before_basis'])
        self.assertEqual(continuity['fee_to_account_at_basis'], 'chain-fee:0xfee-owner')
        self.assertEqual(continuity['fee_to_account_latest_known'], 'chain-fee:0xfee-owner')

    def test_build_materialization_plan_marks_fee_to_continuity_changed_after_basis(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        settled_owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '6',
                'created_at': 1000,
                'from_account': owner,
            }
        ]
        source_repository.position_liquidity_history[(owner, pool_application_id)] = list(
            source_repository.pool_transaction_history[pool_application_id]
        )
        source_repository.pool_fee_to_history[pool_application_id] = [
            {
                'transaction_id': 9,
                'created_at': 900,
                'fee_to_account': 'chain-fee:0xfee-owner-a',
            },
            {
                'transaction_id': 11,
                'created_at': 1100,
                'fee_to_account': 'chain-fee:0xfee-owner-b',
            },
        ]
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                    'owner': settled_owner,
                }
            ]
            )
        )

        continuity = plan['position_replacements'][0]['states'][0]['state_payload_json']['fee_to_continuity']
        self.assertEqual(continuity['continuity_case'], 'changed_after_basis')
        self.assertEqual(continuity['change_count_after_basis'], 1)
        self.assertTrue(continuity['known_before_basis'])
        self.assertEqual(continuity['fee_to_account_at_basis'], 'chain-fee:0xfee-owner-a')
        self.assertEqual(continuity['fee_to_account_latest_known'], 'chain-fee:0xfee-owner-b')

    def test_build_materialization_plan_records_pool_fee_to_account_latest_known(self):
        source_repository = self.FakeSnapshotSourceRepository()
        pool_application_id = '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a'
        source_repository.pool_transaction_history[pool_application_id] = [
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'amount_0_in': '4',
                'amount_0_out': None,
                'amount_1_in': '9',
                'amount_1_out': None,
                'liquidity': '0',
                'created_at': 1000,
                'from_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user',
            }
        ]
        source_repository.pool_fee_to_history[pool_application_id] = [
            {
                'transaction_id': 9,
                'created_at': 900,
                'fee_to_account': 'chain-fee:0xfee-owner-a',
            },
            {
                'transaction_id': 11,
                'created_at': 1100,
                'fee_to_account': 'chain-fee:0xfee-owner-b',
            },
        ]
        builder = PositionMetricsSnapshotBuilder(snapshot_materialization_inputs_repository=source_repository)

        plan = builder.build_materialization_plan(
            self._build_output_batch([
                {
                    'settled_output_type': 'settled_trade',
                    'pool_application_id': pool_application_id,
                    'pool_chain_id': 'chain-a',
                }
            ])
        )

        pool_state = plan['pool_states'][0]
        self.assertEqual(
            pool_state['state_payload_json']['fee_to_account_latest_known'],
            'chain-fee:0xfee-owner-b',
        )


if __name__ == '__main__':
    unittest.main()
