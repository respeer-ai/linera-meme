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
from query.read_models.position_metrics_snapshot_fast_path import PositionMetricsSnapshotFastPath  # noqa: E402
from query.read_models.position_metrics_snapshot_shadow_evaluator import PositionMetricsSnapshotShadowEvaluator  # noqa: E402
from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult  # noqa: E402

_public_api = PositionMetricsBootstrap().public_api()

_build_projection_position_metrics_fetcher = QueryStackReadModelTestSupport.build_projection_position_metrics_fetcher
_replay_summary = QueryStackReadModelTestSupport.replay_summary
_replay_facts = QueryStackReadModelTestSupport.replay_facts
_snapshot_inputs = QueryStackReadModelTestSupport.snapshot_inputs
_build_snapshot_only_repository = QueryStackReadModelTestSupport.build_snapshot_only_repository
_position_metrics_payload = QueryStackReadModelTestSupport.position_metrics_payload
_build_payload_builder = QueryStackReadModelTestSupport.build_payload_builder


class QueryStackProjectionPositionMetricsFetcherMixin:
    def _metrics(self, payload):
        if isinstance(payload, PositionMetricsFetchedResult):
            return payload.projected_metrics
        return self._metrics(payload)

    def _shadow(self, payload):
        if isinstance(payload, PositionMetricsFetchedResult):
            return payload.snapshot_shadow
        return self._shadow(payload)

    def test_projection_position_metrics_fetcher_does_not_use_replay_fallback_on_snapshot_miss(self):
        class FakeRepository:
            def get_replay_facts(self, **_kwargs):
                raise AssertionError('snapshot miss should not load replay facts')

            def get_snapshot_inputs(self, **kwargs):
                self.snapshot_kwargs = dict(kwargs)
                return _snapshot_inputs(
                    position_basis_snapshot={
                        'position_state_id': 'pos-1',
                        'current_liquidity': '2.5',
                    },
                    pool_state_snapshot={
                        'pool_state_id': 'pool-state-1',
                        'current_total_supply': '10',
                        'current_reserve_0': '20',
                        'current_reserve_1': '30',
                        'state_payload_json': {'virtual_initial_liquidity': False},
                    },
                )

        repository = FakeRepository()

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=_build_payload_builder({'data': {}}),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1500,
            })
        )

        self.assertIsInstance(payload, PositionMetricsFetchedResult)
        self.assertEqual(payload.projected_metrics['metrics_status'], 'snapshot_unavailable')
        self.assertEqual(payload.fetch_stage, 'snapshot_unavailable')
        self.assertEqual(payload.fetch_reason_code, 'snapshot_fast_path_miss_no_fallback')
        self.assertIsNone(payload.snapshot_shadow)
        self.assertEqual(
            repository.snapshot_kwargs,
            {'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', 'pool_application_id': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain', 'status': 'active'},
        )

    def test_projection_position_metrics_fetcher_returns_unavailable_when_snapshot_missing(self):
        class FakeRepository:
            def get_replay_facts(self, **_kwargs):
                raise AssertionError('snapshot miss should not load replay facts')

            def get_snapshot_inputs(self, **_kwargs):
                return _snapshot_inputs(
                    position_basis_snapshot=None,
                    pool_state_snapshot={
                        'last_transaction_id': 11,
                        'current_total_supply': '10',
                        'current_reserve_0': '20',
                        'current_reserve_1': '30',
                        'state_payload_json': {'virtual_initial_liquidity': False},
                    },
                )

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=FakeRepository(),
                payload_builder=_build_payload_builder({'data': {}}),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1500,
                'status': 'active',
                'current_liquidity': '7',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'snapshot_unavailable')
        self.assertEqual(self._metrics(payload)['position_liquidity'], '7')
        self.assertIsNone(self._shadow(payload))

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_without_loading_histories(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
                position_basis_snapshot={
                    'status': 'active',
                    'basis_type': 'add_liquidity',
                    'current_liquidity': '7',
                    'basis_transaction_id': 13,
                    'basis_time_ms': 1234,
                },
                pool_state_snapshot={
                    'last_transaction_id': 13,
                    'last_trade_time_ms': None,
                    'last_liquidity_event_time_ms': 1234,
                    'current_total_supply': '10',
                    'current_reserve_0': '20',
                    'current_reserve_1': '30',
                    'fee_free_basis_transaction_id': 13,
                    'fee_free_basis_time_ms': 1234,
                    'fee_free_reserve_0': '14',
                    'fee_free_reserve_1': '21',
                    'fee_free_total_supply': '10',
                    'state_payload_json': {'virtual_initial_liquidity': False},
                },
            )
        )

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1234,
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

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_zero_liquidity_bootstrap_basis(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
                    'last_trade_time_ms': None,
                    'last_liquidity_event_time_ms': 1_800_000_001_000,
                    'fee_free_basis_transaction_id': 3,
                    'fee_free_basis_time_ms': 1_800_000_001_000,
                    'fee_free_reserve_0': '100',
                    'fee_free_reserve_1': '121',
                    'fee_free_total_supply': '110',
                },
            )
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-a', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'},
                total_supply='110.002500227305015907',
                virtual_initial_liquidity=True,
                liquidity='10.002500227305015907',
                amount0='9.095455926391324260',
                amount1='11.002500170477793218',
            )
        )

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10.000227293391365082',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertTrue(self._metrics(payload)['owner_receives_protocol_fees'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_reopen_from_zero_basis(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
                    'last_trade_time_ms': None,
                    'last_liquidity_event_time_ms': 1_800_000_001_000,
                    'fee_free_basis_transaction_id': 3,
                    'fee_free_basis_time_ms': 1_800_000_001_000,
                    'fee_free_reserve_0': '100',
                    'fee_free_reserve_1': '121',
                    'fee_free_total_supply': '110',
                },
            )
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to=None,
                total_supply='110',
                virtual_initial_liquidity=False,
                liquidity='10',
                amount0='9.090909090909090909',
                amount1='11',
            )
        )

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
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
        self.assertEqual(self._metrics(payload)['principal_amount0'], '9.090909090909090909')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '11')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_latest_add_without_current_round_swaps_before_basis(self):
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
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
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
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_later_pool_liquidity_without_intervening_swaps(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to=None,
                total_supply='20',
                virtual_initial_liquidity=False,
                liquidity='5',
                amount0='5',
                amount1='5',
            )
        )

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '5',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '5')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '5')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['exact_case'], 'post_basis_liquidity_changes')

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_opening_mint_with_later_pool_liquidity(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-a', 'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'},
                total_supply='24',
                virtual_initial_liquidity=False,
                liquidity='12',
                amount0='12',
                amount1='12',
            )
        )

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '10')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '10')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount0'], '2')
        self.assertEqual(self._metrics(payload)['protocol_fee_amount1'], '2')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes',
        )

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_materialized_current_principal_after_intervening_swaps(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to=None,
                total_supply='20',
                virtual_initial_liquidity=False,
                liquidity='10',
                amount0='7',
                amount1='22',
            )
        )

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '5')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '20')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '2')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '2')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_materialized_current_principal_with_post_basis_remove_when_fee_to_disabled(self):
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to=None,
                total_supply='9',
                virtual_initial_liquidity=False,
                liquidity='10',
                amount0='4',
                amount1='10',
            )
        )

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '3')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '9')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '1')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '1')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_materialized_current_principal_with_post_basis_remove_when_fee_to_enabled_but_owner_is_not_fee_to(self):
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
        )

        client = _build_payload_builder(
            _position_metrics_payload(
                fee_to={'chain_id': 'chain-fee', 'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd'},
                total_supply='9',
                virtual_initial_liquidity=False,
                liquidity='10',
                amount0='4',
                amount1='10',
            )
        )

        payload = asyncio.run(
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '3')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '9')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '1')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '1')
        self.assertFalse(self._metrics(payload)['owner_receives_protocol_fees'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_owner_materialized_current_principal_with_post_basis_remove_for_opening_add_basis(self):
        repository = _build_snapshot_only_repository(
            _snapshot_inputs(
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
            _build_projection_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=client,
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-fee',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1000,
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
        self.assertTrue(self._metrics(payload)['owner_receives_protocol_fees'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_projection_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_owner_materialized_current_principal_with_latest_remove_basis(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return _snapshot_inputs(
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

            def get_replay_facts(self, **_kwargs):
                raise AssertionError('fast path should not load replay facts')

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
            _build_projection_position_metrics_fetcher(
                product_state_provider=FakeRepository(),
                payload_builder=client,
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
        self.assertTrue(self._metrics(payload)['owner_receives_protocol_fees'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )
