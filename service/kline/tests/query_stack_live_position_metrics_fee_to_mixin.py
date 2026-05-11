import asyncio
import sys
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport
from query_stack_read_model_test_support import QueryStackReadModelTestSupport


QueryStackTestSupport.install()


import kline as kline_module  # noqa: E402
from position_metrics_bootstrap import PositionMetricsBootstrap  # noqa: E402
from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult  # noqa: E402
from query.read_models.position_metrics_snapshot_fast_path import PositionMetricsSnapshotFastPath  # noqa: E402
from query.read_models.position_metrics_snapshot_shadow_evaluator import PositionMetricsSnapshotShadowEvaluator  # noqa: E402

_public_api = PositionMetricsBootstrap().public_api()

_build_live_position_metrics_fetcher = QueryStackReadModelTestSupport.build_live_position_metrics_fetcher
_snapshot_inputs = QueryStackReadModelTestSupport.snapshot_inputs
_build_snapshot_only_repository = QueryStackReadModelTestSupport.build_snapshot_only_repository
_position_metrics_payload = QueryStackReadModelTestSupport.position_metrics_payload
_build_payload_builder = QueryStackReadModelTestSupport.build_payload_builder


class QueryStackLivePositionMetricsFeeToMixin:
    def _metrics(self, payload):
        if isinstance(payload, PositionMetricsFetchedResult):
            return payload.live_metrics
        return self._metrics(payload)

    def _shadow(self, payload):
        if isinstance(payload, PositionMetricsFetchedResult):
            return payload.snapshot_shadow
        return self._shadow(payload)

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_owner_materialized_current_principal_with_post_basis_remove_when_current_owner_protocol_fee_component_is_proven(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'},
                total_supply='12',
                virtual_initial_liquidity=False,
                liquidity='12',
                amount0='6',
                amount1='12',
            )
        )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '5')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '10')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount0'], '1')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount1'], '2')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '0')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '0')
        self.assertTrue(self._metrics(payload)['owner_is_fee_to'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'current_owner_protocol_fee_component_proven',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_safe_fee_to_continuous_nonzero_prior_add_basis(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'},
                total_supply='12',
                virtual_initial_liquidity=False,
                liquidity='12',
                amount0='6',
                amount1='12',
            )
        )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '5')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '10')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount0'], '1')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount1'], '2')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '0')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '0')
        self.assertTrue(self._metrics(payload)['owner_is_fee_to'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_continuous_nonzero_prior_add_basis',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_basis_only_fee_to_nonzero_prior_add_basis(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'},
                total_supply='12',
                virtual_initial_liquidity=False,
                liquidity='12',
                amount0='6',
                amount1='12',
            )
        )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '5')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '10')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount0'], '1')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount1'], '2')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '0')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '0')
        self.assertTrue(self._metrics(payload)['owner_is_fee_to'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_basis_only_nonzero_prior_add_basis',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_historical_protocol_fee_mints_owned_by_current_owner(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return _snapshot_inputs(
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

            def get_replay_facts(self, **_kwargs):
                raise AssertionError('fast path should not load replay facts')

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-fee', 'owner': '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'},
                total_supply='12',
                virtual_initial_liquidity=False,
                liquidity='12',
                amount0='6',
                amount1='12',
            )
        )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=FakeRepository(),
                payload_builder=client,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '5')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '10')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount0'], '1')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount1'], '2')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '0')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '0')
        self.assertFalse(self._metrics(payload)['owner_is_fee_to'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'all_protocol_fee_mints_owned_by_current_owner',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_proven_current_owner_protocol_fee_component(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-fee', 'owner': '0xeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee'},
                total_supply='12',
                virtual_initial_liquidity=False,
                liquidity='12',
                amount0='6',
                amount1='12',
            )
        )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '5')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '10')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount0'], '1')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount1'], '2')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '0')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '0')
        self.assertFalse(self._metrics(payload)['owner_is_fee_to'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'current_owner_protocol_fee_component_proven',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_nonzero_prior_add_basis_when_no_protocol_fee_lp_is_live(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'},
                total_supply='12',
                virtual_initial_liquidity=False,
                liquidity='10',
                amount0='5',
                amount1='10',
            )
        )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '5')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '10')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount0'], '0')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount1'], '0')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '0')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '0')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertIsNone(
            self._shadow(payload)['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case']
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_latest_add_after_prior_current_round_swaps_when_materialized_current_principal_exists(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
                position_basis_snapshot={
                    'status': 'active',
                    'basis_type': 'add_liquidity',
                    'current_liquidity': '7',
                    'basis_transaction_id': 15,
                    'basis_time_ms': 2000,
                    'state_payload_json': {
                        'prior_liquidity_before_basis': '5',
                        'basis_opens_current_round': False,
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to=None,
                total_supply='10',
                virtual_initial_liquidity=False,
                liquidity='7',
                amount0='14',
                amount1='21',
            )
        )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '7',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '14')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '21')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '0')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '0')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_zero_liquidity_bootstrap_with_post_basis_swaps(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-a', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'},
                total_supply='120',
                virtual_initial_liquidity=True,
                liquidity='12',
                amount0='8',
                amount1='12',
            )
        )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '6.666666666666666667')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '10')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
