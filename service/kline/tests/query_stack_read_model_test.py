import asyncio
import sys
import unittest
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport


QueryStackTestSupport.install()


import kline as kline_module  # noqa: E402
from query.read_models.candles import CandlesReadModel  # noqa: E402
from query.read_models.live_position_metrics_fetcher import LivePositionMetricsFetcher  # noqa: E402
from query.read_models.position_metrics import PositionMetricsReadModel  # noqa: E402
from query.read_models.position_metrics_snapshot_fast_path import PositionMetricsSnapshotFastPath  # noqa: E402
from query.read_models.position_metrics_snapshot_shadow_evaluator import PositionMetricsSnapshotShadowEvaluator  # noqa: E402
from query.read_models.positions import PositionsReadModel  # noqa: E402
from query.read_models.transactions import TransactionsReadModel  # noqa: E402
from query.handlers.position_metrics import PositionMetricsHandler  # noqa: E402
from query.serializers.position_metrics import PositionMetricsSerializer  # noqa: E402
from storage.mysql.position_metrics_diagnostic_recorder import PositionMetricsDiagnosticRecorder  # noqa: E402
from storage.mysql.position_metrics_projection_repo import PositionMetricsProjectionRepository  # noqa: E402
from storage.mysql.projection_repo import ProjectionRepository  # noqa: E402


class ReadModelBridgeTest(unittest.TestCase):
    def test_projection_repository_delegates_to_db(self):
        fake_db = QueryStackTestSupport.FakeDb()
        repository = ProjectionRepository(fake_db)

        payload = repository.get_candles(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
            interval='1min',
            pool_id=7,
            pool_application='chain:pool-app',
        )

        self.assertEqual(payload[0], 7)
        self.assertEqual(fake_db.calls[0][0], 'get_kline')
        self.assertEqual(fake_db.calls[0][1]['pool_application'], 'chain:pool-app')

    def test_position_metrics_projection_repository_prefers_direct_settled_repositories(self):
        class FakeSettledTradeProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_pool_transaction_history(self, **kwargs):
                raise AssertionError('should not be called')

            def get_pool_trade_history(self, **kwargs):
                self.calls.append(('get_pool_trade_history', dict(kwargs)))
                return [
                    {'transaction_id': 11, 'created_at': 1200, 'transaction_type': 'BuyToken0'},
                    {'transaction_id': 13, 'created_at': 1600, 'transaction_type': 'SellToken0'},
                ]

        class FakeSettledLiquidityProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_positions(self, **kwargs):
                self.calls.append(('get_positions', dict(kwargs)))
                return [{'pool_id': 5}]

            def get_position_liquidity_history(self, **kwargs):
                self.calls.append(('get_position_liquidity_history', dict(kwargs)))
                return [{'transaction_id': 10}]

            def get_pool_liquidity_history(self, **kwargs):
                self.calls.append(('get_pool_liquidity_history', dict(kwargs)))
                return [{'transaction_id': 12, 'created_at': 1500, 'transaction_type': 'AddLiquidity'}]

        class FakePositionStateProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_position_basis_snapshot(self, **kwargs):
                self.calls.append(('get_position_basis_snapshot', dict(kwargs)))
                return {'position_state_id': 'pos-1'}

        class FakePoolStateProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_pool_state_snapshot(self, **kwargs):
                self.calls.append(('get_pool_state_snapshot', dict(kwargs)))
                return {'pool_state_id': 'pool-state-1'}

        trade_repo = FakeSettledTradeProjectionRepository()
        liquidity_repo = FakeSettledLiquidityProjectionRepository()
        position_state_repo = FakePositionStateProjectionRepository()
        pool_state_repo = FakePoolStateProjectionRepository()
        repository = PositionMetricsProjectionRepository(
            object(),
            settled_trade_projection_repo=trade_repo,
            settled_liquidity_projection_repo=liquidity_repo,
            position_state_projection_repo=position_state_repo,
            pool_state_projection_repo=pool_state_repo,
        )

        self.assertEqual(repository.get_positions(owner='chain:owner-a', status='active'), [{'pool_id': 5}])
        self.assertEqual(
            repository.get_position_liquidity_history(
                owner='chain:owner-a',
                pool_application='chain:pool-app',
                pool_id=5,
            ),
            [{'transaction_id': 10}],
        )
        self.assertEqual(
            repository.get_pool_transaction_history(pool_application='chain:pool-app', pool_id=5),
            [
                {'transaction_id': 11, 'created_at': 1200, 'transaction_type': 'BuyToken0'},
                {'transaction_id': 12, 'created_at': 1500, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 13, 'created_at': 1600, 'transaction_type': 'SellToken0'},
            ],
        )
        self.assertEqual(
            repository.get_pool_swap_count_since(pool_application='chain:pool-app', pool_id=5, created_at=1500),
            1,
        )
        self.assertEqual(
            repository.get_pool_transaction_gap_summary(pool_application='chain:pool-app', pool_id=5),
            {
                'has_internal_gaps': False,
                'start_id': 11,
                'end_id': 13,
                'missing_count': 0,
                'missing_ids_sample': [],
                'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
            },
        )
        self.assertEqual(
            repository.get_position_basis_snapshot(owner='chain:owner-a', pool_application_id='chain:pool-app'),
            {'position_state_id': 'pos-1'},
        )
        self.assertEqual(
            repository.get_pool_state_snapshot(pool_application_id='chain:pool-app'),
            {'pool_state_id': 'pool-state-1'},
        )
        self.assertEqual(
            [call[0] for call in liquidity_repo.calls],
            [
                'get_positions',
                'get_position_liquidity_history',
                'get_pool_liquidity_history',
                'get_pool_liquidity_history',
                'get_pool_liquidity_history',
            ],
        )
        self.assertEqual(
            [call[0] for call in trade_repo.calls],
            ['get_pool_trade_history', 'get_pool_trade_history', 'get_pool_trade_history'],
        )
        self.assertEqual(
            position_state_repo.calls,
            [('get_position_basis_snapshot', {'owner': 'chain:owner-a', 'pool_application_id': 'chain:pool-app', 'status': 'active'})],
        )
        self.assertEqual(pool_state_repo.calls, [('get_pool_state_snapshot', {'pool_application_id': 'chain:pool-app'})])

    def test_read_models_preserve_phase1_contracts(self):
        repository = QueryStackTestSupport.FakeRepository()

        candles = CandlesReadModel(repository).get_points(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
            interval='1min',
        )
        transactions = TransactionsReadModel(repository).get_transactions(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
        )
        positions = PositionsReadModel(repository).get_positions(owner='chain:owner-a', status='active')

        self.assertEqual(candles['pool_id'], 9)
        self.assertEqual(candles['points'], [{'close': '3'}])
        self.assertEqual(transactions, [{'transaction_id': 1}])
        self.assertEqual(positions, {'owner': 'chain:owner-a', 'positions': [{'pool_id': 5}]})

    def test_position_metrics_read_model_preserves_phase1_contract(self):
        repository = QueryStackTestSupport.FakeRepository()

        async def fake_fetcher(position):
            self.assertEqual(position['pool_id'], 5)
            self.assertEqual(position['owner'], 'chain:owner-a')
            return {
                'metrics_status': 'partial_live_redeemable_only',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'computation_blockers': ['missing_history'],
                'fee_amount0': None,
                'fee_amount1': None,
                'protocol_fee_amount0': None,
                'protocol_fee_amount1': None,
            }

        repository.get_positions = lambda **_kwargs: [{
            'pool_application': 'chain:pool-app',
            'pool_id': 5,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'owner': 'chain:owner-a',
            'status': 'active',
            'current_liquidity': '1.23',
        }]
        payload = asyncio.run(
            PositionMetricsReadModel(repository, fake_fetcher).get_position_metrics(
                owner='chain:owner-a',
                status='active',
            )
        )

        self.assertEqual(
            payload,
            {
                'owner': 'chain:owner-a',
                'metrics': [{
                    'pool_application': 'chain:pool-app',
                    'pool_id': 5,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': 'chain:owner-a',
                    'status': 'active',
                    'current_liquidity': '1.23',
                    'metrics_status': 'partial_live_redeemable_only',
                    'exact_fee_supported': False,
                    'exact_principal_supported': False,
                    'computation_blockers': ['missing_history'],
                    'fee_amount0': '0',
                    'fee_amount1': '0',
                    'protocol_fee_amount0': '0',
                    'protocol_fee_amount1': '0',
                    'value_warning_codes': [],
                    'value_warning_message': None,
                }],
            },
        )

    def test_position_metrics_handler_records_only_inexact_rows(self):
        class FakeReadModel:
            async def get_position_metrics(self, **_kwargs):
                return {
                    'owner': 'chain:owner-a',
                    'metrics': [
                        {
                            'owner': 'chain:owner-a',
                            'pool_application': 'chain:pool-app',
                            'pool_id': 5,
                            'status': 'active',
                            'metrics_status': 'partial',
                            'exact_fee_supported': False,
                            'exact_principal_supported': False,
                            'computation_blockers': ['missing_history'],
                            'value_warning_codes': [],
                        },
                        {
                            'owner': 'chain:owner-a',
                            'pool_application': 'chain:pool-app',
                            'pool_id': 6,
                            'status': 'active',
                            'metrics_status': 'exact',
                            'exact_fee_supported': True,
                            'exact_principal_supported': True,
                            'computation_blockers': [],
                            'value_warning_codes': [],
                        },
                    ],
                }

        class FakeDiagnosticRecorder:
            def __init__(self):
                self.rows = []

            def record_inexact_metric(self, metric):
                self.rows.append(dict(metric))

            def record_snapshot_shadow(self, diagnostic):
                self.rows.append({'shadow': dict(diagnostic)})

        recorder = FakeDiagnosticRecorder()
        payload = asyncio.run(
            PositionMetricsHandler(FakeReadModel(), PositionMetricsSerializer(), recorder).get_position_metrics(
                owner='chain:owner-a',
                status='active',
            )
        )

        self.assertEqual(payload['owner'], 'chain:owner-a')
        self.assertEqual(len(recorder.rows), 1)
        self.assertEqual(recorder.rows[0]['pool_id'], 5)
        self.assertEqual(recorder.rows[0]['metrics_status'], 'partial')

    def test_position_metrics_diagnostic_recorder_preserves_event_shape(self):
        class FakeDb:
            def __init__(self):
                self.rows = []

            def record_diagnostic_event(self, **kwargs):
                self.rows.append(dict(kwargs))

        db = FakeDb()
        PositionMetricsDiagnosticRecorder(db).record_inexact_metric(
            {
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'status': 'active',
                'metrics_status': 'partial',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'computation_blockers': ['missing_history'],
                'value_warning_codes': ['estimated_values'],
            }
        )

        self.assertEqual(len(db.rows), 1)
        self.assertEqual(db.rows[0]['source'], 'position_metrics')
        self.assertEqual(db.rows[0]['event_type'], 'inexact_position_metrics')
        self.assertEqual(
            db.rows[0]['details'],
            {
                'metrics_status': 'partial',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'computation_blockers': ['missing_history'],
                'value_warning_codes': ['estimated_values'],
            },
        )

    def test_position_metrics_diagnostic_recorder_preserves_snapshot_shadow_shape(self):
        class FakeDb:
            def __init__(self):
                self.rows = []

            def record_diagnostic_event(self, **kwargs):
                self.rows.append(dict(kwargs))

        db = FakeDb()
        PositionMetricsDiagnosticRecorder(db).record_snapshot_shadow(
            {
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'status': 'active',
                'metrics_status': 'exact',
                'exact_fee_supported': True,
                'exact_principal_supported': True,
                'snapshot_shadow': {
                    'comparable': False,
                    'position_basis_snapshot_present': False,
                    'pool_state_snapshot_present': True,
                    'mismatch_codes': ['missing_position_basis_snapshot'],
                    'readiness': 'snapshot_missing',
                    'readiness_reason_codes': ['missing_position_basis_snapshot'],
                    'exact_case': None,
                    'live_position_status': 'active',
                    'live_current_liquidity': '7',
                    'live_metrics_status': 'exact',
                    'computation_blockers': [],
                    'value_warning_codes': [],
                    'latest_position_transaction_id': 13,
                    'latest_position_created_at': 1234,
                    'latest_pool_transaction_id': 99,
                    'latest_pool_trade_time_ms': 2200,
                    'latest_pool_liquidity_event_time_ms': 2100,
                    'position_basis_snapshot': None,
                    'pool_state_snapshot': {'last_transaction_id': 99},
                },
            }
        )

        self.assertEqual(len(db.rows), 1)
        self.assertEqual(db.rows[0]['event_type'], 'snapshot_shadow_gap')
        self.assertEqual(
            db.rows[0]['details'],
            {
                'metrics_status': 'exact',
                'exact_fee_supported': True,
                'exact_principal_supported': True,
                'comparable': False,
                'position_basis_snapshot_present': False,
                'pool_state_snapshot_present': True,
                'mismatch_codes': ['missing_position_basis_snapshot'],
                'readiness': 'snapshot_missing',
                'readiness_reason_codes': ['missing_position_basis_snapshot'],
                'exact_case': None,
                'live_position_status': 'active',
                'live_current_liquidity': '7',
                'live_metrics_status': 'exact',
                'computation_blockers': [],
                'value_warning_codes': [],
                'latest_position_transaction_id': 13,
                'latest_position_created_at': 1234,
                'latest_pool_transaction_id': 99,
                'latest_pool_trade_time_ms': 2200,
                'latest_pool_liquidity_event_time_ms': 2100,
                'position_basis_snapshot': None,
                'pool_state_snapshot': {'last_transaction_id': 99},
            },
        )

    def test_position_metrics_handler_records_snapshot_shadow_and_hides_internal_payload(self):
        class FakeReadModel:
            async def get_position_metrics(self, **_kwargs):
                return {
                    'owner': 'chain:owner-a',
                    'metrics': [
                        {
                            'pool_application': 'chain:pool-app',
                            'pool_id': 5,
                            'owner': 'chain:owner-a',
                            'status': 'active',
                            'metrics_status': 'exact',
                            'exact_fee_supported': True,
                            'exact_principal_supported': True,
                            'computation_blockers': [],
                            'value_warning_codes': [],
                        },
                    ],
                    '_shadow_diagnostics': [
                        {
                            'owner': 'chain:owner-a',
                            'pool_application': 'chain:pool-app',
                            'pool_id': 5,
                            'status': 'active',
                            'metrics_status': 'exact',
                            'exact_fee_supported': False,
                            'exact_principal_supported': True,
                            'snapshot_shadow': {
                                'mismatch_codes': [],
                                'readiness': 'financial_semantics_pending',
                                'readiness_reason_codes': ['exact_fee_not_supported'],
                            },
                        }
                    ],
                }

        class FakeDiagnosticRecorder:
            def __init__(self):
                self.inexact_rows = []
                self.shadow_rows = []

            def record_inexact_metric(self, metric):
                self.inexact_rows.append(dict(metric))

            def record_snapshot_shadow(self, diagnostic):
                self.shadow_rows.append(dict(diagnostic))

        recorder = FakeDiagnosticRecorder()
        payload = asyncio.run(
            PositionMetricsHandler(FakeReadModel(), PositionMetricsSerializer(), recorder).get_position_metrics(
                owner='chain:owner-a',
                status='active',
            )
        )

        self.assertEqual(payload['owner'], 'chain:owner-a')
        self.assertNotIn('_shadow_diagnostics', payload)
        self.assertEqual(recorder.inexact_rows, [])
        self.assertEqual(len(recorder.shadow_rows), 1)
        self.assertEqual(recorder.shadow_rows[0]['pool_id'], 5)

    def test_live_position_metrics_fetcher_uses_repository_histories(self):
        class FakeRepository:
            def get_position_liquidity_history(self, **kwargs):
                self.liquidity_kwargs = dict(kwargs)
                return [{'transaction_id': 10}]

            def get_pool_transaction_history(self, **kwargs):
                self.transaction_kwargs = dict(kwargs)
                return [{'transaction_id': 11}]

            def get_pool_swap_count_since(self, **kwargs):
                self.swap_count_kwargs = dict(kwargs)
                return 3

            def get_pool_transaction_gap_summary(self, **kwargs):
                self.gap_kwargs = dict(kwargs)
                return {'has_internal_gaps': False}

            def get_snapshot_inputs(self, **kwargs):
                self.snapshot_kwargs = dict(kwargs)
                return {
                    'position_basis_snapshot': {'position_state_id': 'pos-1'},
                    'pool_state_snapshot': {'pool_state_id': 'pool-state-1'},
                }

        class FakePoolApplicationClient:
            def __init__(self):
                self.calls = []

            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                self.calls.append((pool_application, dict(owner)))
                return {'data': {'latestTransactions': []}}

        repository = FakeRepository()
        client = FakePoolApplicationClient()
        captured = {}

        def fake_enrich_position_metrics_from_payload(position, payload, **kwargs):
            captured['position'] = dict(position)
            captured['payload'] = dict(payload)
            captured.update(kwargs)
            return {'metrics_status': 'ok'}

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=repository,
                pool_application_client=client,
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=fake_enrich_position_metrics_from_payload,
            )({
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1500,
            })
        )

        self.assertEqual(payload, {'metrics_status': 'ok'})
        self.assertEqual(client.calls, [('chain:pool-app', {'chain_id': 'chain', 'owner': 'owner-a'})])
        self.assertEqual(captured['payload'], {'data': {'latestTransactions': []}})
        self.assertEqual(captured['liquidity_history'], [{'transaction_id': 10}])
        self.assertEqual(captured['pool_transaction_history'], [{'transaction_id': 11}])
        self.assertEqual(captured['pool_swap_count_since_open'], 3)
        self.assertEqual(captured['pool_history_gap_summary'], {'has_internal_gaps': False})
        self.assertEqual(captured['position_basis_snapshot'], {'position_state_id': 'pos-1'})
        self.assertEqual(captured['pool_state_snapshot'], {'pool_state_id': 'pool-state-1'})
        self.assertEqual(
            repository.snapshot_kwargs,
            {'owner': 'chain:owner-a', 'pool_application_id': 'chain:pool-app', 'status': 'active'},
        )

    def test_live_position_metrics_fetcher_returns_shadow_evaluation_when_enabled(self):
        class FakeRepository:
            def get_position_liquidity_history(self, **_kwargs):
                return [{'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'}]

            def get_pool_transaction_history(self, **_kwargs):
                return [{'transaction_id': 11, 'created_at': 2000, 'transaction_type': 'BuyToken0'}]

            def get_pool_swap_count_since(self, **_kwargs):
                return 1

            def get_pool_transaction_gap_summary(self, **_kwargs):
                return {'has_internal_gaps': False}

            def get_snapshot_inputs(self, **_kwargs):
                return {'position_basis_snapshot': None, 'pool_state_snapshot': {'last_transaction_id': 11}}

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {'data': {'latestTransactions': []}}

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: {
                    'metrics_status': 'exact',
                    'exact_fee_supported': True,
                    'exact_principal_supported': True,
                },
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1500,
                'status': 'active',
                'current_liquidity': '7',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['mismatch_codes'],
            ['missing_position_basis_snapshot', 'pool_last_trade_time_mismatch'],
        )
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'snapshot_missing')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['readiness_reason_codes'],
            ['missing_position_basis_snapshot', 'pool_last_trade_time_mismatch'],
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_without_loading_histories(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
                        'status': 'active',
                        'basis_type': 'add_liquidity',
                        'current_liquidity': '7',
                        'basis_transaction_id': 13,
                        'basis_time_ms': 1234,
                    },
                    'pool_state_snapshot': {
                        'last_transaction_id': 13,
                        'last_trade_time_ms': None,
                        'last_liquidity_event_time_ms': 1234,
                        'fee_free_basis_transaction_id': 13,
                        'fee_free_basis_time_ms': 1234,
                        'fee_free_reserve_0': '14',
                        'fee_free_reserve_1': '21',
                        'fee_free_total_supply': '10',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': None},
                        'totalSupply': '10',
                        'virtualInitialLiquidity': False,
                        'liquidity': {'liquidity': '7', 'amount0': '14', 'amount1': '21'},
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1234,
                'status': 'active',
                'current_liquidity': '7',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '14')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '21')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_zero_liquidity_bootstrap_basis(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 3,
                        'last_trade_time_ms': None,
                        'last_liquidity_event_time_ms': 1_800_000_001_000,
                        'fee_free_basis_transaction_id': 3,
                        'fee_free_basis_time_ms': 1_800_000_001_000,
                        'fee_free_reserve_0': '100',
                        'fee_free_reserve_1': '121',
                        'fee_free_total_supply': '110',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
                        'totalSupply': '110.002500227305015907',
                        'virtualInitialLiquidity': True,
                        'liquidity': {
                            'liquidity': '10.002500227305015907',
                            'amount0': '9.095455926391324260',
                            'amount1': '11.002500170477793218',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10.000227293391365082',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertTrue(payload['live_metrics']['owner_is_fee_to'])
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_reopen_from_zero_basis(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 3,
                        'last_trade_time_ms': None,
                        'last_liquidity_event_time_ms': 1_800_000_001_000,
                        'fee_free_basis_transaction_id': 3,
                        'fee_free_basis_time_ms': 1_800_000_001_000,
                        'fee_free_reserve_0': '100',
                        'fee_free_reserve_1': '121',
                        'fee_free_total_supply': '110',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': None},
                        'totalSupply': '110',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '10',
                            'amount0': '9.090909090909090909',
                            'amount1': '11',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '9.090909090909090909')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '11')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_latest_add_without_current_round_swaps_before_basis(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 15,
                        'last_trade_time_ms': 900,
                        'last_liquidity_event_time_ms': 2000,
                        'fee_free_basis_transaction_id': 15,
                        'fee_free_basis_time_ms': 2000,
                        'fee_free_reserve_0': '14',
                        'fee_free_reserve_1': '21',
                        'fee_free_total_supply': '10',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': None},
                        'totalSupply': '10',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '7',
                            'amount0': '14',
                            'amount1': '21',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '7',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '14')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '21')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_later_pool_liquidity_without_intervening_swaps(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
                        'status': 'active',
                        'basis_type': 'remove_liquidity',
                        'current_liquidity': '5',
                        'basis_transaction_id': 15,
                        'basis_time_ms': 1000,
                        'state_payload_json': {
                            'trade_count_between_basis_and_fee_free_basis': 0,
                        },
                    },
                    'pool_state_snapshot': {
                        'last_transaction_id': 16,
                        'last_trade_time_ms': 900,
                        'last_liquidity_event_time_ms': 1100,
                        'fee_free_basis_transaction_id': 16,
                        'fee_free_basis_time_ms': 1100,
                        'fee_free_reserve_0': '20',
                        'fee_free_reserve_1': '20',
                        'fee_free_total_supply': '20',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': None},
                        'totalSupply': '20',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '5',
                            'amount0': '5',
                            'amount1': '5',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '5',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '5')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['exact_case'], 'post_basis_liquidity_changes')

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_opening_mint_with_later_pool_liquidity(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 16,
                        'last_trade_time_ms': None,
                        'last_liquidity_event_time_ms': 1100,
                        'fee_free_basis_transaction_id': 16,
                        'fee_free_basis_time_ms': 1100,
                        'fee_free_reserve_0': '24',
                        'fee_free_reserve_1': '24',
                        'fee_free_total_supply': '24',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
                        'totalSupply': '24',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '12',
                            'amount0': '12',
                            'amount1': '12',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '10')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount0'], '2')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_materialized_current_principal_after_intervening_swaps(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 13,
                        'last_trade_time_ms': 1300,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '11',
                        'fee_free_reserve_1': '40',
                        'fee_free_total_supply': '20',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': None},
                        'totalSupply': '20',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '10',
                            'amount0': '7',
                            'amount1': '22',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '20')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '2')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '2')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_materialized_current_principal_with_post_basis_remove_when_fee_to_disabled(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '5',
                        'fee_free_reserve_1': '18',
                        'fee_free_total_supply': '9',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': None},
                        'totalSupply': '9',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '10',
                            'amount0': '4',
                            'amount1': '10',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '3')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '9')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '1')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '1')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_materialized_current_principal_with_post_basis_remove_when_fee_to_enabled_but_owner_is_not_fee_to(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '5',
                        'fee_free_reserve_1': '18',
                        'fee_free_total_supply': '9',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
                        'totalSupply': '9',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '10',
                            'amount0': '4',
                            'amount1': '10',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '3')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '9')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '1')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '1')
        self.assertFalse(payload['live_metrics']['owner_is_fee_to'])
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_owner_materialized_current_principal_with_post_basis_remove_for_opening_add_basis(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '6',
                        'fee_free_reserve_1': '12',
                        'fee_free_total_supply': '12',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
                        'totalSupply': '12',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '12',
                            'amount0': '6',
                            'amount1': '12',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertTrue(payload['live_metrics']['owner_is_fee_to'])
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_owner_materialized_current_principal_with_latest_remove_basis(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '6',
                        'fee_free_reserve_1': '12',
                        'fee_free_total_supply': '12',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
                        'totalSupply': '12',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '12',
                            'amount0': '6',
                            'amount1': '12',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertTrue(payload['live_metrics']['owner_is_fee_to'])
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_owner_materialized_current_principal_with_post_basis_remove_when_current_owner_protocol_fee_component_is_proven(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '6',
                        'fee_free_reserve_1': '12',
                        'fee_free_total_supply': '12',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
                        'totalSupply': '12',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '12',
                            'amount0': '6',
                            'amount1': '12',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertTrue(payload['live_metrics']['owner_is_fee_to'])
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'current_owner_protocol_fee_component_proven',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_safe_fee_to_continuous_nonzero_prior_add_basis(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '6',
                        'fee_free_reserve_1': '12',
                        'fee_free_total_supply': '12',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
                        'totalSupply': '12',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '12',
                            'amount0': '6',
                            'amount1': '12',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertTrue(payload['live_metrics']['owner_is_fee_to'])
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_continuous_nonzero_prior_add_basis',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_basis_only_fee_to_nonzero_prior_add_basis(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '6',
                        'fee_free_reserve_1': '12',
                        'fee_free_total_supply': '12',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
                        'totalSupply': '12',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '12',
                            'amount0': '6',
                            'amount1': '12',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertTrue(payload['live_metrics']['owner_is_fee_to'])
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'fee_to_basis_only_nonzero_prior_add_basis',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_historical_protocol_fee_mints_owned_by_current_owner(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '6',
                        'fee_free_reserve_1': '12',
                        'fee_free_total_supply': '12',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xother-owner'}},
                        'totalSupply': '12',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '12',
                            'amount0': '6',
                            'amount1': '12',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertFalse(payload['live_metrics']['owner_is_fee_to'])
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'all_protocol_fee_mints_owned_by_current_owner',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_proven_current_owner_protocol_fee_component(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '6',
                        'fee_free_reserve_1': '12',
                        'fee_free_total_supply': '12',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xother-owner'}},
                        'totalSupply': '12',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '12',
                            'amount0': '6',
                            'amount1': '12',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount0'], '1')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount1'], '2')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertFalse(payload['live_metrics']['owner_is_fee_to'])
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case'],
            'current_owner_protocol_fee_component_proven',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_fee_to_nonzero_prior_add_basis_when_no_protocol_fee_lp_is_live(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 12,
                        'last_trade_time_ms': 1100,
                        'last_liquidity_event_time_ms': 1200,
                        'fee_free_basis_transaction_id': 12,
                        'fee_free_basis_time_ms': 1200,
                        'fee_free_reserve_0': '6',
                        'fee_free_reserve_1': '12',
                        'fee_free_total_supply': '12',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-fee', 'owner': '0xfee-owner'}},
                        'totalSupply': '12',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '10',
                            'amount0': '5',
                            'amount1': '10',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-fee:0xfee-owner',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 900,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '5')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['protocol_fee_amount1'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertIsNone(
            payload['snapshot_shadow']['snapshot_shadow']['position_basis_snapshot']['materialized_protocol_fee_split_case']
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_latest_add_after_prior_current_round_swaps_when_materialized_current_principal_exists(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 16,
                        'last_trade_time_ms': 1500,
                        'last_liquidity_event_time_ms': 2000,
                        'fee_free_basis_transaction_id': 16,
                        'fee_free_basis_time_ms': 2100,
                        'fee_free_reserve_0': '20',
                        'fee_free_reserve_1': '30',
                        'fee_free_total_supply': '10',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': None},
                        'totalSupply': '10',
                        'virtualInitialLiquidity': False,
                        'liquidity': {
                            'liquidity': '7',
                            'amount0': '14',
                            'amount1': '21',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1000,
                'status': 'active',
                'current_liquidity': '7',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '14')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '21')
        self.assertEqual(payload['live_metrics']['fee_amount0'], '0')
        self.assertEqual(payload['live_metrics']['fee_amount1'], '0')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
        self.assertEqual(
            payload['snapshot_shadow']['snapshot_shadow']['exact_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )

    def test_live_position_metrics_fetcher_uses_snapshot_fast_path_for_zero_liquidity_bootstrap_with_post_basis_swaps(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return {
                    'position_basis_snapshot': {
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
                    'pool_state_snapshot': {
                        'last_transaction_id': 20,
                        'last_trade_time_ms': 1_800_000_001_300,
                        'last_liquidity_event_time_ms': 1_800_000_001_000,
                        'fee_free_basis_transaction_id': 15,
                        'fee_free_basis_time_ms': 1_800_000_001_000,
                        'fee_free_reserve_0': '80',
                        'fee_free_reserve_1': '120',
                        'fee_free_total_supply': '120',
                    },
                }

            def get_position_liquidity_history(self, **_kwargs):
                raise AssertionError('fast path should not load liquidity history')

            def get_pool_transaction_history(self, **_kwargs):
                raise AssertionError('fast path should not load pool transaction history')

            def get_pool_swap_count_since(self, **_kwargs):
                raise AssertionError('fast path should not count swaps')

            def get_pool_transaction_gap_summary(self, **_kwargs):
                raise AssertionError('fast path should not inspect gap summary')

        class FakePoolApplicationClient:
            async def get_position_metrics_payload(self, *, pool_application: str, owner: dict):
                return {
                    'data': {
                        'pool': {'fee_to': {'chain_id': 'chain-a', 'owner': '0xowner-a'}},
                        'totalSupply': '120',
                        'virtualInitialLiquidity': True,
                        'liquidity': {
                            'liquidity': '12',
                            'amount0': '8',
                            'amount1': '12',
                        },
                        'latestTransactions': [],
                    }
                }

        payload = asyncio.run(
            LivePositionMetricsFetcher(
                repository=FakeRepository(),
                pool_application_client=FakePoolApplicationClient(),
                parse_owner_account=kline_module.position_metrics.parse_account,
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                snapshot_fast_path=PositionMetricsSnapshotFastPath(),
                snapshot_shadow_evaluator=PositionMetricsSnapshotShadowEvaluator(),
            )({
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 5,
                'opened_at': 1_800_000_000_000,
                'status': 'active',
                'current_liquidity': '10',
            })
        )

        self.assertEqual(payload['live_metrics']['metrics_status'], 'exact_no_swap_history')
        self.assertEqual(payload['live_metrics']['principal_amount0'], '6.666666666666666667')
        self.assertEqual(payload['live_metrics']['principal_amount1'], '10')
        self.assertEqual(payload['snapshot_shadow']['snapshot_shadow']['readiness'], 'candidate')
