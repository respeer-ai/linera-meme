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
from position_metrics_payload_decision import PositionMetricsPayloadDecision  # noqa: E402
from position_metrics_payload_result import PositionMetricsPayloadResult  # noqa: E402

_public_api = PositionMetricsBootstrap().public_api()

_build_live_position_metrics_fetcher = QueryStackReadModelTestSupport.build_live_position_metrics_fetcher
_replay_summary = QueryStackReadModelTestSupport.replay_summary
_replay_facts = QueryStackReadModelTestSupport.replay_facts
_snapshot_inputs = QueryStackReadModelTestSupport.snapshot_inputs
_build_snapshot_only_repository = QueryStackReadModelTestSupport.build_snapshot_only_repository
_position_metrics_payload = QueryStackReadModelTestSupport.position_metrics_payload
_build_payload_builder = QueryStackReadModelTestSupport.build_payload_builder


class QueryStackLivePositionMetricsFetcherMixin:
    def _metrics(self, payload):
        if isinstance(payload, PositionMetricsFetchedResult):
            return payload.live_metrics
        return self._metrics(payload)

    def _shadow(self, payload):
        if isinstance(payload, PositionMetricsFetchedResult):
            return payload.snapshot_shadow
        return self._shadow(payload)

    def test_live_position_metrics_fetcher_uses_repository_histories(self):
        class FakeRepository:
            def get_replay_facts(self, **kwargs):
                self.replay_kwargs = dict(kwargs)
                return _replay_facts(
                    liquidity_history=[{'transaction_id': 10}],
                    pool_transaction_history=[
                        {
                            'transaction_id': 11,
                            'created_at': 1499,
                            'transaction_type': 'AddLiquidity',
                            'from_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                        },
                        {'transaction_id': 12, 'created_at': 1500, 'transaction_type': 'BuyToken0'},
                        {'transaction_id': 13, 'created_at': 1600, 'transaction_type': 'SellToken0'},
                        {'transaction_id': 14, 'created_at': 1700, 'transaction_type': 'BuyToken0'},
                    ],
                    pool_swap_count_since_open=3,
                    pool_history_gap_summary={'has_internal_gaps': False},
                    replay_summary=_replay_summary(
                        latest_position_transaction_id=10,
                        latest_pool_transaction_id=14,
                        latest_pool_trade_time_ms=1700,
                        latest_pool_liquidity_event_time_ms=1499,
                    ),
                )

            def get_snapshot_inputs(self, **kwargs):
                self.snapshot_kwargs = dict(kwargs)
                return _snapshot_inputs(
                    position_basis_snapshot={
                        'position_state_id': 'pos-1',
                        'current_liquidity': '2.5',
                    },
                    pool_state_snapshot={
                        'pool_state_id': 'pool-state-1',
                        'live_total_supply': '10',
                        'live_reserve_0': '20',
                        'live_reserve_1': '30',
                        'state_payload_json': {'virtual_initial_liquidity': False},
                    },
                )

        repository = FakeRepository()
        captured = {}

        def fake_enrich_position_metrics_from_payload(position, payload, **kwargs):
            captured['position'] = dict(position)
            captured['payload'] = dict(payload)
            captured.update(kwargs)
            return PositionMetricsPayloadResult(
                metrics={'metrics_status': 'ok'},
                decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                reason_code='payload_requires_history',
            )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=repository,
                payload_builder=_build_payload_builder({'data': {}}),
                plan_payload=lambda *_args, **_kwargs: PositionMetricsPayloadResult(
                    metrics={'metrics_status': 'partial_live_redeemable_only'},
                    decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                    reason_code='payload_requires_history',
                ),
                enrich_payload=fake_enrich_position_metrics_from_payload,
            )({
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'opened_at': 1500,
            })
        )

        self.assertIsInstance(payload, PositionMetricsFetchedResult)
        self.assertEqual(payload.live_metrics, {'metrics_status': 'ok'})
        self.assertEqual(payload.fetch_stage, 'replay_fallback')
        self.assertEqual(
            payload.fetch_reason_code,
            'snapshot_fast_path_miss_payload_requires_history',
        )
        self.assertEqual(captured['payload'], {'data': {}})
        self.assertEqual(
            captured['replay_bundle'].liquidity_history(),
            [
                {'transaction_id': 10}
            ],
        )
        self.assertEqual(
            captured['replay_bundle'].pool_transaction_history(),
            [
                {
                    'transaction_id': 11,
                    'created_at': 1499,
                    'transaction_type': 'AddLiquidity',
                    'from_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                },
                {'transaction_id': 12, 'created_at': 1500, 'transaction_type': 'BuyToken0'},
                {'transaction_id': 13, 'created_at': 1600, 'transaction_type': 'SellToken0'},
                {'transaction_id': 14, 'created_at': 1700, 'transaction_type': 'BuyToken0'},
            ],
        )
        self.assertEqual(captured['replay_bundle'].pool_swap_count_since_open(), 3)
        self.assertEqual(
            captured['replay_bundle'].pool_history_gap_summary(),
            {'has_internal_gaps': False},
        )
        self.assertEqual(captured['position_basis_snapshot'].raw()['position_state_id'], 'pos-1')
        self.assertEqual(captured['position_basis_snapshot'].raw()['semantic_facts'], {
            'prior_liquidity_before_basis': None,
            'has_only_zero_liquidity_before_basis': None,
            'basis_opens_current_round': None,
            'current_round_liquidity_event_count': None,
            'current_round_started_at': None,
            'current_round_started_transaction_id': None,
            'current_round_trade_count_before_basis': None,
            'trade_count_between_basis_and_fee_free_basis': None,
            'exact_current_principal_case': None,
            'principal_amount_0_current': None,
            'principal_amount_1_current': None,
            'post_basis_remove_count': None,
            'basis_protocol_fee_liquidity_minted': None,
            'post_basis_protocol_fee_liquidity_minted': None,
            'post_basis_protocol_fee_mint_event_count': None,
            'post_basis_protocol_fee_liquidity_minted_before_first_add': None,
            'fee_to_continuous_protocol_fee_liquidity_current': None,
            'protocol_fee_liquidity_provenance_case': None,
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
        })
        self.assertEqual(captured['pool_state_snapshot'].raw()['pool_state_id'], 'pool-state-1')
        self.assertEqual(captured['pool_state_snapshot'].live_total_supply(), '10')
        self.assertEqual(
            repository.snapshot_kwargs,
            {'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', 'pool_application_id': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain', 'status': 'active'},
        )
        self.assertEqual(
            repository.replay_kwargs,
            {'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', 'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain', 'pool_id': 5, 'opened_at': 1500},
        )

    def test_live_position_metrics_fetcher_returns_shadow_evaluation_when_enabled(self):
        class FakeRepository:
            def get_replay_facts(self, **_kwargs):
                return _replay_facts(
                    liquidity_history=[{'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'}],
                    pool_transaction_history=[{'transaction_id': 11, 'created_at': 2000, 'transaction_type': 'BuyToken0'}],
                    pool_swap_count_since_open=1,
                    pool_history_gap_summary={'has_internal_gaps': False},
                    replay_summary=_replay_summary(
                        latest_position_transaction_id=10,
                        latest_position_created_at=1000,
                        latest_pool_transaction_id=11,
                        latest_pool_trade_time_ms=2000,
                    ),
                )

            def get_snapshot_inputs(self, **_kwargs):
                return _snapshot_inputs(
                    position_basis_snapshot=None,
                    pool_state_snapshot={
                        'last_transaction_id': 11,
                        'live_total_supply': '10',
                        'live_reserve_0': '20',
                        'live_reserve_1': '30',
                        'state_payload_json': {'virtual_initial_liquidity': False},
                    },
                )

        payload = asyncio.run(
            _build_live_position_metrics_fetcher(
                product_state_provider=FakeRepository(),
                payload_builder=_build_payload_builder({'data': {}}),
                plan_payload=lambda *_args, **_kwargs: PositionMetricsPayloadResult(
                    metrics={
                        'metrics_status': 'partial_live_redeemable_only',
                        'exact_fee_supported': True,
                        'exact_principal_supported': True,
                    },
                    decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                    reason_code='payload_requires_history',
                ),
                enrich_payload=lambda *_args, **_kwargs: PositionMetricsPayloadResult(
                    metrics={
                        'metrics_status': 'exact',
                        'exact_fee_supported': True,
                        'exact_principal_supported': True,
                    },
                    decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                    reason_code='payload_requires_history',
                ),
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

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['mismatch_codes'],
            ['missing_position_basis_snapshot', 'pool_last_trade_time_mismatch'],
        )
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'snapshot_missing')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['readiness_reason_codes'],
            ['missing_position_basis_snapshot', 'pool_last_trade_time_mismatch'],
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_without_loading_histories(self):
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
                    'live_total_supply': '10',
                    'live_reserve_0': '20',
                    'live_reserve_1': '30',
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
            _build_live_position_metrics_fetcher(
                product_state_provider=repository,
                plan_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass payload planning')
                ),
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
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

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_zero_liquidity_bootstrap_basis(self):
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
                'current_liquidity': '10.000227293391365082',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertTrue(self._metrics(payload)['owner_is_fee_to'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_reopen_from_zero_basis(self):
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
        self.assertEqual(self._metrics(payload)['principal_amount0'], '9.090909090909090909')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '11')
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_latest_add_without_current_round_swaps_before_basis(self):
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
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_later_pool_liquidity_without_intervening_swaps(self):
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

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_opening_mint_with_later_pool_liquidity(self):
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

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_materialized_current_principal_after_intervening_swaps(self):
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

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_materialized_current_principal_with_post_basis_remove_when_fee_to_disabled(self):
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

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_materialized_current_principal_with_post_basis_remove_when_fee_to_enabled_but_owner_is_not_fee_to(self):
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
                'current_liquidity': '10',
            })
        )

        self.assertEqual(self._metrics(payload)['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(self._metrics(payload)['principal_amount0'], '3')
        self.assertEqual(self._metrics(payload)['principal_amount1'], '9')
        self.assertEqual(self._metrics(payload)['fee_amount0'], '1')
        self.assertEqual(self._metrics(payload)['fee_amount1'], '1')
        self.assertFalse(self._metrics(payload)['owner_is_fee_to'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_owner_materialized_current_principal_with_post_basis_remove_for_opening_add_basis(self):
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
        self.assertTrue(self._metrics(payload)['owner_is_fee_to'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_owner_materialized_current_principal_with_latest_remove_basis(self):
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
        self.assertTrue(self._metrics(payload)['owner_is_fee_to'])
        self.assertEqual(self._shadow(payload)['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            self._shadow(payload)['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )
