import asyncio
import sys
import unittest
from collections import Counter
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport
from query_stack_read_model_test_support import QueryStackReadModelTestSupport
from query_stack_live_position_metrics_fee_to_mixin import QueryStackLivePositionMetricsFeeToMixin
from query_stack_live_position_metrics_fetcher_mixin import QueryStackLivePositionMetricsFetcherMixin


QueryStackTestSupport.install()


from query.read_models.candles import CandlesReadModel  # noqa: E402
from query.read_models.position_metrics import PositionMetricsReadModel  # noqa: E402
from query.read_models.position_metrics_read_result import PositionMetricsReadResult  # noqa: E402
from query.read_models.positions import PositionsReadModel  # noqa: E402
from query.read_models.transactions import TransactionsReadModel  # noqa: E402
from query.handlers.position_metrics import PositionMetricsHandler  # noqa: E402
from query.serializers.position_metrics import PositionMetricsSerializer  # noqa: E402
from storage.mysql.position_metrics_diagnostic_recorder import PositionMetricsDiagnosticRecorder  # noqa: E402
from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError  # noqa: E402
from storage.mysql.position_metrics_positions_projection_repo import PositionMetricsPositionsProjectionRepository  # noqa: E402
from storage.mysql.position_metrics_replay_facts_projection_repo import PositionMetricsReplayFactsProjectionRepository  # noqa: E402
from storage.mysql.position_metrics_snapshot_inputs_projection_repo import PositionMetricsSnapshotInputsProjectionRepository  # noqa: E402
from storage.mysql.settled_pool_history_projection_repo import SettledPoolHistoryProjectionRepository  # noqa: E402

_recorded_method_names = QueryStackReadModelTestSupport.recorded_method_names


class ReadModelBridgeTest(
    QueryStackLivePositionMetricsFetcherMixin,
    QueryStackLivePositionMetricsFeeToMixin,
    unittest.TestCase,
):
    def test_candles_read_model_uses_direct_settled_trade_projection_contract(self):
        class FakeSettledTradeProjectionRepository:
            def get_candles(self, **kwargs):
                self.kwargs = dict(kwargs)
                return (7, 'chain:pool-app', 'AAA', 'BBB', [{'timestamp': 100, 'close': '1.23'}])

        trade_repo = FakeSettledTradeProjectionRepository()
        payload = CandlesReadModel(trade_repo).get_points(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
            interval='1min',
            pool_id=7,
            pool_application='chain:pool-app',
        )

        self.assertEqual(payload['pool_id'], 7)
        self.assertEqual(trade_repo.kwargs['pool_application'], 'chain:pool-app')

    def test_position_metrics_snapshot_and_replay_repositories_prefer_direct_projection_contracts(self):
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
        snapshot_repository = PositionMetricsSnapshotInputsProjectionRepository(
            object(),
            position_state_projection_repo=position_state_repo,
            pool_state_projection_repo=pool_state_repo,
        )
        replay_repository = PositionMetricsReplayFactsProjectionRepository(
            settled_liquidity_projection_repo=liquidity_repo,
            settled_pool_history_projection_repo=SettledPoolHistoryProjectionRepository(
                settled_trade_projection_repo=trade_repo,
                settled_liquidity_projection_repo=liquidity_repo,
            ),
        )

        snapshot_inputs = snapshot_repository.get_snapshot_inputs(
            owner='chain:owner-a',
            pool_application_id='chain:pool-app',
        )
        self.assertEqual(
            snapshot_inputs.position_basis_snapshot().raw(),
            {'position_state_id': 'pos-1'},
        )
        self.assertEqual(
            snapshot_inputs.pool_state_snapshot().raw(),
            {'pool_state_id': 'pool-state-1'},
        )
        replay_facts = replay_repository.get_replay_facts(
            owner='chain:owner-a',
            pool_application='chain:pool-app',
            pool_id=5,
            opened_at=1500,
        )
        self.assertEqual(
            replay_facts.liquidity_history(),
            [{'transaction_id': 10}],
        )
        self.assertEqual(
            replay_facts.pool_transaction_history(),
            [
                {'transaction_id': 11, 'created_at': 1200, 'transaction_type': 'BuyToken0'},
                {'transaction_id': 12, 'created_at': 1500, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 13, 'created_at': 1600, 'transaction_type': 'SellToken0'},
            ],
        )
        self.assertEqual(replay_facts.pool_swap_count_since_open(), 1)
        self.assertEqual(
            replay_facts.pool_history_gap_summary(),
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
            replay_facts.replay_summary().as_dict(),
            {
                'latest_position_transaction_id': 10,
                'latest_position_created_at': None,
                'latest_pool_transaction_id': 13,
                'latest_pool_trade_time_ms': 1600,
                'latest_pool_liquidity_event_time_ms': 1500,
            },
        )
        self.assertEqual(
            Counter(_recorded_method_names(liquidity_repo.calls)),
            Counter(
                {
                    'get_position_liquidity_history': 1,
                    'get_pool_liquidity_history': 3,
                }
            ),
        )
        self.assertEqual(
            Counter(_recorded_method_names(trade_repo.calls)),
            Counter({'get_pool_trade_history': 3}),
        )
        self.assertEqual(
            position_state_repo.calls,
            [('get_position_basis_snapshot', {'owner': 'chain:owner-a', 'pool_application_id': 'chain:pool-app', 'status': 'active'})],
        )
        self.assertEqual(pool_state_repo.calls, [('get_pool_state_snapshot', {'pool_application_id': 'chain:pool-app'})])
        self.assertTrue(
            all(call[1]['pool_application'] == 'chain:pool-app' for call in trade_repo.calls),
        )
        self.assertTrue(
            all(call[1]['pool_id'] == 5 for call in trade_repo.calls),
        )
        self.assertTrue(
            all(call[1]['pool_application'] == 'chain:pool-app' for call in liquidity_repo.calls if 'pool_application' in call[1]),
        )

    def test_position_metrics_positions_projection_repository_uses_settled_liquidity_projection_repository(self):
        class FakeSettledLiquidityProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_positions(self, **kwargs):
                self.calls.append(('get_positions', dict(kwargs)))
                return [{'pool_id': 5}]

        liquidity_repo = FakeSettledLiquidityProjectionRepository()
        repository = PositionMetricsPositionsProjectionRepository(
            object(),
            settled_liquidity_projection_repo=liquidity_repo,
        )

        self.assertEqual(
            repository.get_positions(owner='chain:owner-a', status='active'),
            [{'pool_id': 5}],
        )
        self.assertEqual(
            liquidity_repo.calls,
            [('get_positions', {'owner': 'chain:owner-a', 'status': 'active'})],
        )

    def test_replay_summary_uses_canonical_created_at_row_time(self):
        class FakeSettledTradeProjectionRepository:
            def get_pool_trade_history(self, **_kwargs):
                return [
                    {'transaction_id': 11, 'created_at': 1200, 'transaction_type': 'BuyToken0'},
                    {'transaction_id': 12, 'created_at': 1600, 'transaction_type': 'SellToken0'},
                ]

        class FakeSettledLiquidityProjectionRepository:
            def get_position_liquidity_history(self, **_kwargs):
                return [{'transaction_id': 10, 'created_at': 1100, 'transaction_type': 'AddLiquidity'}]

            def get_pool_liquidity_history(self, **_kwargs):
                return [{'transaction_id': 10, 'created_at': 1100, 'transaction_type': 'AddLiquidity'}]

        replay_repository = PositionMetricsReplayFactsProjectionRepository(
            settled_liquidity_projection_repo=FakeSettledLiquidityProjectionRepository(),
            settled_pool_history_projection_repo=SettledPoolHistoryProjectionRepository(
                settled_trade_projection_repo=FakeSettledTradeProjectionRepository(),
                settled_liquidity_projection_repo=FakeSettledLiquidityProjectionRepository(),
            ),
        )

        replay_facts = replay_repository.get_replay_facts(
            owner='chain:owner-a',
            pool_application='chain:pool-app',
            pool_id=5,
            opened_at=1000,
        )

        self.assertEqual(
            replay_facts.replay_summary().as_dict(),
            {
                'latest_position_transaction_id': 10,
                'latest_position_created_at': 1100,
                'latest_pool_transaction_id': 12,
                'latest_pool_trade_time_ms': 1600,
                'latest_pool_liquidity_event_time_ms': 1100,
            },
        )

    def test_shared_pool_transaction_history_projection_boundary_is_reusable(self):
        class FakeTradeProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_pool_trade_history(self, **kwargs):
                self.calls.append(('get_pool_trade_history', dict(kwargs)))
                return [{'transaction_id': 11, 'created_at': 2000, 'transaction_type': 'BuyToken0'}]

        class FakeLiquidityProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_position_liquidity_history(self, **kwargs):
                self.calls.append(('get_position_liquidity_history', dict(kwargs)))
                return [{'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'}]

            def get_pool_liquidity_history(self, **kwargs):
                self.calls.append(('get_pool_liquidity_history', dict(kwargs)))
                return [{'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'}]

        trade_repo = FakeTradeProjectionRepository()
        liquidity_repo = FakeLiquidityProjectionRepository()
        settled_pool_history_repo = SettledPoolHistoryProjectionRepository(
            settled_trade_projection_repo=trade_repo,
            settled_liquidity_projection_repo=liquidity_repo,
        )

        position_metrics_replay_repository = PositionMetricsReplayFactsProjectionRepository(
            settled_liquidity_projection_repo=liquidity_repo,
            settled_pool_history_projection_repo=settled_pool_history_repo,
        )

        self.assertEqual(
            settled_pool_history_repo.get_pool_transaction_history(
                pool_application='chain:pool-app',
                pool_id=5,
            ),
            [
                {'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 11, 'created_at': 2000, 'transaction_type': 'BuyToken0'},
            ],
        )
        self.assertEqual(
            position_metrics_replay_repository.get_replay_facts(
                owner='chain:owner-a',
                pool_application='chain:pool-app',
                pool_id=5,
                opened_at=1500,
            ).pool_transaction_history(),
            [
                {'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 11, 'created_at': 2000, 'transaction_type': 'BuyToken0'},
            ],
        )
        self.assertEqual(
            Counter(_recorded_method_names(trade_repo.calls)),
            Counter({'get_pool_trade_history': 4}),
        )
        self.assertEqual(
            Counter(_recorded_method_names(liquidity_repo.calls)),
            Counter({'get_pool_liquidity_history': 4, 'get_position_liquidity_history': 1}),
        )

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

        self.assertIsInstance(payload, PositionMetricsReadResult)
        self.assertEqual(
            payload.public_payload(),
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
        self.assertEqual(payload.shadow_diagnostics, [])

    def test_position_metrics_handler_records_only_inexact_rows(self):
        class FakeReadModel:
            async def get_position_metrics(self, **_kwargs):
                return PositionMetricsReadResult(
                    owner='chain:owner-a',
                    metrics=[
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
                    metric_diagnostics=[
                        {
                            'pool_application': 'chain:pool-app',
                            'pool_id': 5,
                            'owner': 'chain:owner-a',
                            'status': 'active',
                            'metrics_status': 'partial',
                            'exact_fee_supported': False,
                            'exact_principal_supported': False,
                            'computation_blockers': ['missing_history'],
                            'value_warning_codes': [],
                            'fetch_stage': 'payload_only',
                            'fetch_reason_code': 'snapshot_fast_path_miss_payload_only',
                        },
                        {
                            'pool_application': 'chain:pool-app',
                            'pool_id': 6,
                            'owner': 'chain:owner-a',
                            'status': 'active',
                            'metrics_status': 'exact',
                            'exact_fee_supported': True,
                            'exact_principal_supported': True,
                            'computation_blockers': [],
                            'value_warning_codes': [],
                            'fetch_stage': 'snapshot_fast_path',
                            'fetch_reason_code': 'snapshot_fast_path_hit',
                        },
                    ],
                )

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
                'fetch_stage': 'payload_only',
                'fetch_reason_code': 'snapshot_fast_path_miss_payload_only',
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
                'fetch_stage': 'payload_only',
                'fetch_reason_code': 'snapshot_fast_path_miss_payload_only',
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
                'fetch_stage': 'replay_fallback',
                'fetch_reason_code': 'snapshot_fast_path_miss_payload_requires_history',
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
                'fetch_stage': 'replay_fallback',
                'fetch_reason_code': 'snapshot_fast_path_miss_payload_requires_history',
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

    def test_positions_read_model_returns_envelope(self):
        class FakeRepository:
            def get_positions(self, *, owner, status):
                return [
                    {'pool_id': 1, 'status': 'active'},
                    {'pool_id': 2, 'status': 'closed'},
                ]

        read_model = PositionsReadModel(FakeRepository())
        result = read_model.get_positions(owner='chain:owner-a', status='active')

        self.assertEqual(result['owner'], 'chain:owner-a')
        self.assertEqual(len(result['positions']), 2)
        self.assertEqual(result['positions'][0]['pool_id'], 1)
        self.assertEqual(result['positions'][1]['pool_id'], 2)

    def test_positions_read_model_raises_on_none_repository_result(self):
        class FakeRepository:
            def get_positions(self, *, owner, status):
                return None

        read_model = PositionsReadModel(FakeRepository())
        with self.assertRaises(ProjectionQueryUnavailableError):
            read_model.get_positions(owner='chain:owner-a', status='active')

    def test_position_metrics_handler_records_snapshot_shadow_and_hides_internal_payload(self):
        class FakeReadModel:
            async def get_position_metrics(self, **_kwargs):
                return PositionMetricsReadResult(
                    owner='chain:owner-a',
                    metrics=[
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
                    metric_diagnostics=[
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
                            'fetch_stage': 'snapshot_fast_path',
                            'fetch_reason_code': 'snapshot_fast_path_hit',
                        },
                    ],
                    shadow_diagnostics=[
                        {
                            'owner': 'chain:owner-a',
                            'pool_application': 'chain:pool-app',
                            'pool_id': 5,
                            'status': 'active',
                            'fetch_stage': 'snapshot_fast_path',
                            'fetch_reason_code': 'snapshot_fast_path_hit',
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
                )

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
        self.assertEqual(recorder.inexact_rows, [])
        self.assertEqual(len(recorder.shadow_rows), 1)
        self.assertEqual(recorder.shadow_rows[0]['pool_id'], 5)
        self.assertEqual(recorder.shadow_rows[0]['fetch_stage'], 'snapshot_fast_path')
        self.assertEqual(recorder.shadow_rows[0]['fetch_reason_code'], 'snapshot_fast_path_hit')
