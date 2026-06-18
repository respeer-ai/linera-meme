import asyncio
import sys
import unittest
from collections import Counter
from decimal import Decimal
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport
from query_stack_read_model_test_support import QueryStackReadModelTestSupport
from query_stack_projection_position_metrics_fee_to_mixin import QueryStackProjectionPositionMetricsFeeToMixin
from query_stack_projection_position_metrics_fetcher_mixin import QueryStackProjectionPositionMetricsFetcherMixin


QueryStackTestSupport.install()


from query.read_models.candles import CandlesReadModel  # noqa: E402
from query.read_models.position_metrics import PositionMetricsReadModel  # noqa: E402
from query.read_models.position_metrics_read_result import PositionMetricsReadResult  # noqa: E402
from query.read_models.positions import PositionsReadModel  # noqa: E402
from query.read_models.transactions import TransactionsReadModel  # noqa: E402
from query.handlers.position_metrics import PositionMetricsHandler  # noqa: E402
from storage.mysql.position_metrics_diagnostic_recorder import PositionMetricsDiagnosticRecorder  # noqa: E402
from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError  # noqa: E402
from storage.mysql.position_metrics_positions_projection_repo import PositionMetricsPositionsProjectionRepository  # noqa: E402
from storage.mysql.position_metrics_replay_facts_projection_repo import PositionMetricsReplayFactsProjectionRepository  # noqa: E402
from storage.mysql.position_metrics_snapshot_inputs_projection_repo import PositionMetricsSnapshotInputsProjectionRepository  # noqa: E402
from storage.mysql.settled_pool_history_projection_repo import SettledPoolHistoryProjectionRepository  # noqa: E402

_recorded_method_names = QueryStackReadModelTestSupport.recorded_method_names


class ReadModelBridgeTest(
    QueryStackProjectionPositionMetricsFetcherMixin,
    QueryStackProjectionPositionMetricsFeeToMixin,
    unittest.TestCase,
):
    def test_candles_read_model_uses_direct_settled_trade_projection_contract(self):
        class FakeSettledTradeProjectionRepository:
            def get_candles(self, **kwargs):
                self.kwargs = dict(kwargs)
                return (7, '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain', 'AAA', 'BBB', [{'timestamp': 100, 'close': '1.23'}])

        trade_repo = FakeSettledTradeProjectionRepository()
        payload = CandlesReadModel(trade_repo).get_points(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
            interval='1min',
            pool_id=7,
            pool_application='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
        )

        self.assertEqual(payload['pool_id'], 7)
        self.assertEqual(trade_repo.kwargs['pool_application'], '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain')

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
            owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
            pool_application_id='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
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
            owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
            pool_application='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
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
            [('get_position_basis_snapshot', {'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', 'pool_application_id': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain', 'status': 'active'})],
        )
        self.assertEqual(pool_state_repo.calls, [('get_pool_state_snapshot', {'pool_application_id': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain'})])
        self.assertTrue(
            all(call[1]['pool_application'] == '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain' for call in trade_repo.calls),
        )
        self.assertTrue(
            all(call[1]['pool_id'] == 5 for call in trade_repo.calls),
        )
        self.assertTrue(
            all(call[1]['pool_application'] == '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain' for call in liquidity_repo.calls if 'pool_application' in call[1]),
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
            repository.get_positions(owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', status='active'),
            [{'pool_id': 5}],
        )
        self.assertEqual(
            liquidity_repo.calls,
            [('get_positions', {'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', 'status': 'active'})],
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
            owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
            pool_application='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
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
                pool_application='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                pool_id=5,
            ),
            [
                {'transaction_id': 10, 'created_at': 1000, 'transaction_type': 'AddLiquidity'},
                {'transaction_id': 11, 'created_at': 2000, 'transaction_type': 'BuyToken0'},
            ],
        )
        self.assertEqual(
            position_metrics_replay_repository.get_replay_facts(
                owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                pool_application='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
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
        positions = asyncio.run(
            PositionsReadModel(repository).get_positions(owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', status='active')
        )

        self.assertEqual(candles['pool_id'], 9)
        self.assertEqual(candles['points'], [{'close': '3'}])
        self.assertEqual(transactions, [{'transaction_id': 1}])
        self.assertEqual(positions['owner'], '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain')
        self.assertEqual(positions['positions'][0]['pool_id'], 5)

    def test_position_metrics_read_model_preserves_phase1_contract(self):
        repository = QueryStackTestSupport.FakeRepository()

        async def fake_fetcher(position):
            self.assertEqual(position['pool_id'], 5)
            self.assertEqual(position['owner'], '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain')
            return {
                'metrics_status': 'partial_projected_redeemable_only',
                'fee_calculation_complete': False,
                'principal_calculation_complete': False,
                'computation_blockers': ['missing_history'],
                'fee_amount0': None,
                'fee_amount1': None,
                'protocol_fee_amount0': None,
                'protocol_fee_amount1': None,
            }

        repository.get_positions = lambda **_kwargs: [{
            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
            'pool_id': 5,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
            'status': 'active',
            'current_liquidity': '1.23',
        }]
        payload = asyncio.run(
            PositionMetricsReadModel(repository, fake_fetcher).get_position_metrics(
                owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                status='active',
            )
        )

        self.assertIsInstance(payload, PositionMetricsReadResult)
        self.assertEqual(
            payload.public_payload(),
            {
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'metrics': [{
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                    'pool_id': 5,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                    'status': 'active',
                    'current_liquidity': '1.23',
                    'computation_blockers': ['missing_history'],
                    'fee_amount0': '0',
                    'fee_amount1': '0',
                    'protocol_fee_amount0': '0',
                    'protocol_fee_amount1': '0',
                    'trailing_24h_fee_amount0': '0',
                    'trailing_24h_fee_amount1': '0',
                    'value_warning_codes': [],
                    'value_warning_message': None,
                }],
            },
        )
        self.assertEqual(payload.shadow_diagnostics, [])

    def test_position_metrics_read_model_returns_synthetic_protocol_fee_receiver_metrics(self):
        repository = QueryStackTestSupport.FakeRepository()

        async def fake_fetcher(_position):
            raise AssertionError('synthetic protocol fee receiver position should not use projection fetcher')

        repository.get_positions = lambda **_kwargs: [{
            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
            'pool_id': 5,
            'token_0': 'AAA',
            'token_1': 'BBB',
            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
            'status': 'virtual',
            'current_liquidity': '0',
            'position_kind': 'virtual_initial_liquidity',
            'is_virtual_position': True,
            'protocol_fee_receiver_account': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
            'protocol_fee_reference_amount0': '25',
            'protocol_fee_reference_amount1': '0',
        }]
        payload = asyncio.run(
            PositionMetricsReadModel(repository, fake_fetcher).get_position_metrics(
                owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                status='active',
            )
        )

        self.assertIsInstance(payload, PositionMetricsReadResult)
        self.assertEqual(
            payload.public_payload(),
            {
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'metrics': [{
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                    'pool_id': 5,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                    'status': 'virtual',
                    'current_liquidity': '0',
                    'position_liquidity': '0',
                    'total_supply': None,
                    'redeemable_amount0': '0',
                    'redeemable_amount1': '0',
                    'virtual_initial_liquidity': True,
                    'computation_blockers': [],
                    'principal_amount0': '0',
                    'principal_amount1': '0',
                    'fee_amount0': '0',
                    'fee_amount1': '0',
                    'protocol_fee_amount0': '0',
                    'protocol_fee_amount1': '0',
                    'trailing_24h_fee_amount0': '0',
                    'trailing_24h_fee_amount1': '0',
                    'trailing_24h_fee_window_start_ms': None,
                    'trailing_24h_fee_window_end_ms': None,
                    'value_warning_codes': ['virtual_initial_liquidity_protocol_fee_receiver_position'],
                    'value_warning_message': (
                        'Virtual initial liquidity is pool-level, not owner-held LP. '
                        'This synthetic position marks the protocol fee receiver while '
                        'projection state is not available.'
                    ),
                    'share_ratio': None,
                }],
            },
        )
        self.assertEqual(payload.shadow_diagnostics, [])
        self.assertEqual(payload.metric_diagnostics[0]['fetch_stage'], 'synthetic_virtual_position')
        self.assertEqual(
            payload.metric_diagnostics[0]['fetch_reason_code'],
            'virtual_initial_liquidity',
        )

    def test_position_metrics_read_model_ignores_pool_fee_free_basis_materialized_protocol_fee(self):
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain'
        base_payload = self._virtual_protocol_fee_metrics_payload(
            owner=owner,
            materialized_protocol_fee_liquidity='7',
            latest_fee_to_account=owner,
            current_total_supply='130',
            fee_free_total_supply='100',
            current_reserve_0='260',
            current_reserve_1='390',
            pool_fee_free_basis_protocol_fee_minted_after='1',
        )
        changed_payload = self._virtual_protocol_fee_metrics_payload(
            owner=owner,
            materialized_protocol_fee_liquidity='7',
            latest_fee_to_account=owner,
            current_total_supply='130',
            fee_free_total_supply='100',
            current_reserve_0='260',
            current_reserve_1='390',
            pool_fee_free_basis_protocol_fee_minted_after='999999999999999999999999',
        )

        base_metric = base_payload.public_payload()['metrics'][0]
        changed_metric = changed_payload.public_payload()['metrics'][0]
        self.assertEqual(changed_metric['position_liquidity'], base_metric['position_liquidity'])
        self.assertEqual(changed_metric['protocol_fee_amount0'], base_metric['protocol_fee_amount0'])
        self.assertEqual(changed_metric['protocol_fee_amount1'], base_metric['protocol_fee_amount1'])

    def test_position_metrics_read_model_uses_full_history_protocol_fee_liquidity_for_virtual_position(self):
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain'

        payload = self._virtual_protocol_fee_metrics_payload(
            owner=owner,
            materialized_protocol_fee_liquidity='7',
            full_materialized_protocol_fee_liquidity='37',
            latest_fee_to_account=owner,
            current_total_supply='130',
            fee_free_total_supply='100',
            current_reserve_0='260',
            current_reserve_1='390',
        )

        metric = payload.public_payload()['metrics'][0]
        self.assertEqual(metric['position_liquidity'], '37')
        self.assertEqual(metric['protocol_fee_amount0'], '74')
        self.assertEqual(metric['protocol_fee_amount1'], '111')

    def test_position_metrics_read_model_uses_pool_total_minted_fee_when_receiver_facts_are_missing(self):
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain'

        payload = self._virtual_protocol_fee_metrics_payload(
            owner=owner,
            materialized_protocol_fee_liquidity='0',
            latest_fee_to_account=owner,
            current_total_supply='130',
            fee_free_total_supply='100',
            current_reserve_0='260',
            current_reserve_1='390',
            total_minted_protocol_fee='83',
            pending_protocol_fee='0.25',
        )

        metric = payload.public_payload()['metrics'][0]
        self.assertEqual(metric['position_liquidity'], '83.25')
        self.assertEqual(metric['total_supply'], '130.25')
        self.assertEqual(metric['protocol_fee_amount0'], '166.180422264875239923')
        self.assertEqual(metric['protocol_fee_amount1'], '249.270633397312859885')

    def test_position_metrics_read_model_does_not_use_pool_total_minted_fee_after_owner_remove(self):
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain'

        payload = self._virtual_protocol_fee_metrics_payload(
            owner=owner,
            materialized_protocol_fee_liquidity='19',
            full_materialized_protocol_fee_liquidity='19',
            latest_fee_to_account=owner,
            current_total_supply='130',
            fee_free_total_supply='100',
            current_reserve_0='260',
            current_reserve_1='390',
            total_minted_protocol_fee='37',
        )

        metric = payload.public_payload()['metrics'][0]
        self.assertEqual(metric['position_liquidity'], '19')
        self.assertEqual(metric['protocol_fee_amount0'], '38')
        self.assertEqual(metric['protocol_fee_amount1'], '57')

    def test_position_metrics_read_model_subtracts_skipped_remove_from_total_minted_fee_fallback(self):
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain'

        payload = self._virtual_protocol_fee_metrics_payload(
            owner=owner,
            materialized_protocol_fee_liquidity='0',
            latest_fee_to_account=owner,
            current_total_supply='130',
            fee_free_total_supply='100',
            current_reserve_0='260',
            current_reserve_1='390',
            total_minted_protocol_fee='37',
            skipped_position_remove_liquidity='25',
        )

        metric = payload.public_payload()['metrics'][0]
        self.assertEqual(metric['position_liquidity'], '12')
        self.assertEqual(metric['protocol_fee_amount0'], '24')
        self.assertEqual(metric['protocol_fee_amount1'], '36')

    def test_position_metrics_read_model_exposes_protocol_fee_trailing_24h_for_virtual_position(self):
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain'

        payload = self._virtual_protocol_fee_metrics_payload(
            owner=owner,
            materialized_protocol_fee_liquidity='7',
            full_materialized_protocol_fee_liquidity='37',
            latest_fee_to_account=owner,
            current_total_supply='130',
            fee_free_total_supply='100',
            current_reserve_0='260',
            current_reserve_1='390',
            trailing_24h_fee_amount_0='1.25',
            trailing_24h_fee_amount_1='0.5',
            trailing_24h_fee_window_start_ms=1000,
            trailing_24h_fee_window_end_ms=86401000,
        )

        metric = payload.public_payload()['metrics'][0]
        self.assertEqual(metric['trailing_24h_fee_amount0'], '1.25')
        self.assertEqual(metric['trailing_24h_fee_amount1'], '0.5')
        self.assertEqual(metric['trailing_24h_fee_window_start_ms'], 1000)
        self.assertEqual(metric['trailing_24h_fee_window_end_ms'], 86401000)

    def test_position_metrics_read_model_does_not_use_basis_scoped_protocol_fee_for_virtual_position(self):
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain'

        payload = self._virtual_protocol_fee_metrics_payload(
            owner=owner,
            materialized_protocol_fee_liquidity='7',
            latest_fee_to_account=owner,
            current_total_supply='130',
            fee_free_total_supply='100',
            current_reserve_0='260',
            current_reserve_1='390',
        )

        metric = payload.public_payload()['metrics'][0]
        self.assertEqual(metric['position_liquidity'], '0')
        self.assertEqual(metric['protocol_fee_amount0'], '0')
        self.assertEqual(metric['protocol_fee_amount1'], '0')
        self.assertEqual(
            metric['value_warning_message'],
            (
                'Virtual initial liquidity is pool-level, not owner-held LP. '
                'This synthetic position marks the protocol fee receiver while '
                'projection state is not available.'
            ),
        )

    def _virtual_protocol_fee_metrics_payload(
        self,
        *,
        owner,
        materialized_protocol_fee_liquidity,
        latest_fee_to_account,
        full_materialized_protocol_fee_liquidity=None,
        current_total_supply,
        fee_free_total_supply,
        current_reserve_0,
        current_reserve_1,
        pool_fee_free_basis_protocol_fee_minted_after=None,
        trailing_24h_fee_amount_0=None,
        trailing_24h_fee_amount_1=None,
        trailing_24h_fee_window_start_ms=None,
        trailing_24h_fee_window_end_ms=None,
        total_minted_protocol_fee=None,
        pending_protocol_fee='0',
        skipped_position_remove_liquidity=None,
    ):
        repository = QueryStackTestSupport.FakeRepository()

        async def fake_fetcher(_position):
            raise AssertionError('virtual initial protocol fee receiver should use projection state')

        class FakeSnapshotInputs:
            def position_basis_snapshot(self):
                semantic_facts = {
                    'protocol_fee_liquidity_owned_by_current_owner_current': (
                        materialized_protocol_fee_liquidity
                    ),
                }
                state_payload_json = {}
                if skipped_position_remove_liquidity is not None:
                    state_payload_json['skipped_position_remove_liquidity'] = (
                        skipped_position_remove_liquidity
                    )
                if full_materialized_protocol_fee_liquidity is not None:
                    semantic_facts['full_protocol_fee_liquidity_owned_by_current_owner'] = (
                        full_materialized_protocol_fee_liquidity
                    )
                if latest_fee_to_account is not None:
                    semantic_facts['fee_to_account_latest_known'] = latest_fee_to_account
                if trailing_24h_fee_amount_0 is not None:
                    semantic_facts['trailing_24h_fee_amount_0'] = trailing_24h_fee_amount_0
                if trailing_24h_fee_amount_1 is not None:
                    semantic_facts['trailing_24h_fee_amount_1'] = trailing_24h_fee_amount_1
                if trailing_24h_fee_window_start_ms is not None:
                    semantic_facts['trailing_24h_fee_window_start_ms'] = trailing_24h_fee_window_start_ms
                if trailing_24h_fee_window_end_ms is not None:
                    semantic_facts['trailing_24h_fee_window_end_ms'] = trailing_24h_fee_window_end_ms
                return {
                    'semantic_facts': semantic_facts,
                    'state_payload_json': state_payload_json,
                }

            def pool_state_snapshot(self):
                state_payload_json = {'virtual_initial_liquidity': True}
                if pool_fee_free_basis_protocol_fee_minted_after is not None:
                    state_payload_json['fee_free_basis'] = {
                        'protocol_fee_minted_after': pool_fee_free_basis_protocol_fee_minted_after,
                    }
                return {
                    'current_reserve_0': current_reserve_0,
                    'current_reserve_1': current_reserve_1,
                    'current_total_supply': current_total_supply,
                    'fee_free_total_supply': fee_free_total_supply,
                    'total_minted_protocol_fee': (
                        total_minted_protocol_fee
                        if total_minted_protocol_fee is not None
                        else full_materialized_protocol_fee_liquidity or '0'
                    ),
                    'pending_protocol_fee': pending_protocol_fee,
                    'state_payload_json': state_payload_json,
                }

        class FakeSnapshotInputsRepository:
            def get_snapshot_inputs(self, **kwargs):
                if kwargs.get('status') == 'active':
                    return FakeSnapshotInputs()
                return None

        class FakeVirtualPositionsReadModel:
            snapshot_inputs_projection_repository = FakeSnapshotInputsRepository()

            async def enrich_positions(self, **kwargs):
                return kwargs['positions']

        repository.get_positions = lambda **_kwargs: [{
            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
            'pool_id': 5,
            'token_0': 'AAA',
            'token_1': 'TLINERA',
            'owner': owner,
            'status': 'virtual',
            'current_liquidity': '0',
            'position_kind': 'virtual_initial_liquidity',
            'is_virtual_position': True,
            'protocol_fee_receiver_account': owner,
            'protocol_fee_reference_amount0': '0',
            'protocol_fee_reference_amount1': '0',
        }]
        return asyncio.run(
            PositionMetricsReadModel(
                repository,
                fake_fetcher,
                virtual_positions_read_model=FakeVirtualPositionsReadModel(),
            ).get_position_metrics(owner=owner, status='virtual')
        )

    def test_position_metrics_handler_records_only_inexact_rows(self):
        class FakeReadModel:
            async def get_position_metrics(self, **_kwargs):
                return PositionMetricsReadResult(
                    owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                    metrics=[
                        {
                            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                            'pool_id': 5,
                            'status': 'active',
                            'metrics_status': 'partial',
                            'fee_calculation_complete': False,
                            'principal_calculation_complete': False,
                            'computation_blockers': ['missing_history'],
                            'value_warning_codes': [],
                        },
                        {
                            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                            'pool_id': 6,
                            'status': 'active',
                            'metrics_status': 'exact',
                            'fee_calculation_complete': True,
                            'principal_calculation_complete': True,
                            'computation_blockers': [],
                            'value_warning_codes': [],
                        },
                    ],
                    metric_diagnostics=[
                        {
                            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                            'pool_id': 5,
                            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                            'status': 'active',
                            'metrics_status': 'partial',
                            'fee_calculation_complete': False,
                            'principal_calculation_complete': False,
                            'computation_blockers': ['missing_history'],
                            'value_warning_codes': [],
                            'fetch_stage': 'snapshot_unavailable',
                            'fetch_reason_code': 'snapshot_fast_path_miss_no_fallback',
                        },
                        {
                            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                            'pool_id': 6,
                            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                            'status': 'active',
                            'metrics_status': 'exact',
                            'fee_calculation_complete': True,
                            'principal_calculation_complete': True,
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
            PositionMetricsHandler(FakeReadModel(), recorder).get_position_metrics(
                owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                status='active',
            )
        )

        self.assertEqual(payload['owner'], '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain')
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
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'status': 'active',
                'fetch_stage': 'snapshot_unavailable',
                'fetch_reason_code': 'snapshot_fast_path_miss_no_fallback',
                'metrics_status': 'partial',
                'fee_calculation_complete': False,
                'principal_calculation_complete': False,
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
                'fetch_stage': 'snapshot_unavailable',
                'fetch_reason_code': 'snapshot_fast_path_miss_no_fallback',
                'metrics_status': 'partial',
                'fee_calculation_complete': False,
                'principal_calculation_complete': False,
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
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                'pool_id': 5,
                'status': 'active',
                'fetch_stage': 'snapshot_unavailable',
                'fetch_reason_code': 'snapshot_fast_path_miss_no_fallback',
                'metrics_status': 'exact',
                'fee_calculation_complete': True,
                'principal_calculation_complete': True,
                'snapshot_shadow': {
                    'comparable': False,
                    'position_basis_snapshot_present': False,
                    'pool_state_snapshot_present': True,
                    'mismatch_codes': ['missing_position_basis_snapshot'],
                    'readiness': 'snapshot_missing',
                    'readiness_reason_codes': ['missing_position_basis_snapshot'],
                    'exact_case': None,
                    'projected_position_status': 'active',
                    'projected_current_liquidity': '7',
                    'projected_metrics_status': 'exact',
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
                'fetch_stage': 'snapshot_unavailable',
                'fetch_reason_code': 'snapshot_fast_path_miss_no_fallback',
                'metrics_status': 'exact',
                'fee_calculation_complete': True,
                'principal_calculation_complete': True,
                'comparable': False,
                'position_basis_snapshot_present': False,
                'pool_state_snapshot_present': True,
                'mismatch_codes': ['missing_position_basis_snapshot'],
                'readiness': 'snapshot_missing',
                'readiness_reason_codes': ['missing_position_basis_snapshot'],
                'exact_case': None,
                'projected_position_status': 'active',
                'projected_current_liquidity': '7',
                'projected_metrics_status': 'exact',
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
                    {
                        'pool_application': '0xpool1@chain',
                        'pool_id': 1,
                        'token_0': 'AAA',
                        'token_1': 'BBB',
                        'status': 'active',
                    },
                    {
                        'pool_application': '0xpool2@chain',
                        'pool_id': 2,
                        'token_0': 'CCC',
                        'token_1': 'DDD',
                        'status': 'closed',
                    },
                ]

        read_model = PositionsReadModel(FakeRepository())
        result = asyncio.run(read_model.get_positions(owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', status='active'))

        self.assertEqual(result['owner'], '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain')
        self.assertEqual(len(result['positions']), 1)
        self.assertEqual(result['positions'][0]['pool_id'], 1)

    def test_positions_read_model_raises_on_none_repository_result(self):
        class FakeRepository:
            def get_positions(self, *, owner, status):
                return None

        read_model = PositionsReadModel(FakeRepository())
        with self.assertRaises(ProjectionQueryUnavailableError):
            asyncio.run(read_model.get_positions(owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', status='active'))

    def test_positions_read_model_keeps_closed_actual_position_closed_when_virtual_lmm_exists(self):
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain'

        class FakeRepository:
            def get_positions(self, *, owner, status):
                self.calls = (owner, status)
                return [{
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                    'pool_id': 1,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': owner,
                    'status': 'closed',
                    'current_liquidity': '0',
                    'added_liquidity': '1.2',
                    'removed_liquidity': '2.0',
                    'add_tx_count': 1,
                    'remove_tx_count': 1,
                    'opened_at': 1000,
                    'updated_at': 2000,
                    'closed_at': 2000,
                }]

        class FakeVirtualPositionsReadModel:
            async def enrich_positions(self, *, owner, status, positions):
                self.calls = (owner, status, list(positions))
                return list(positions) + [{
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                    'pool_id': 1,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': owner,
                    'status': 'virtual',
                    'current_liquidity': '5.123456789123456789',
                    'added_liquidity': '5.123456789123456789',
                    'removed_liquidity': '0',
                    'add_tx_count': 1,
                    'remove_tx_count': 0,
                    'opened_at': 900,
                    'updated_at': 3000,
                    'closed_at': None,
                    'position_kind': 'virtual_initial_liquidity',
                    'is_virtual_position': True,
                    'virtual_initial_amount0': '100',
                    'virtual_initial_amount1': '1',
                    'protocol_fee_receiver_account': owner,
                    'protocol_fee_reference_amount0': '100',
                    'protocol_fee_reference_amount1': '1',
                }]

        repository = FakeRepository()
        virtual_positions = FakeVirtualPositionsReadModel()
        read_model = PositionsReadModel(
            repository,
            virtual_positions_read_model=virtual_positions,
        )

        result = asyncio.run(read_model.get_positions(owner=owner, status='all'))

        self.assertEqual(repository.calls, (owner, 'all'))
        self.assertEqual(virtual_positions.calls[0:2], (owner, 'all'))
        self.assertEqual(len(result['positions']), 1)
        position = result['positions'][0]
        self.assertEqual(position['status'], 'closed')
        self.assertEqual(position['current_liquidity'], '0')
        self.assertEqual(position['virtual_current_liquidity'], '5.123456789123456789')
        self.assertEqual(position['closed_at'], 2000)
        self.assertIsNone(position['position_kind'])
        self.assertIsNone(position['is_virtual_position'])
        self.assertEqual(position['virtual_initial_amount0'], '100')
        self.assertEqual(position['protocol_fee_receiver_account'], owner)

    def test_positions_read_model_returns_active_virtual_initial_display_position_when_no_actual_liquidity_exists(self):
        owner = '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain'

        class FakeRepository:
            def get_positions(self, *, owner, status):
                return [{
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                    'pool_id': 1,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': owner,
                    'status': 'closed',
                    'current_liquidity': '0',
                    'added_liquidity': '1.2',
                    'removed_liquidity': '1.2',
                    'add_tx_count': 1,
                    'remove_tx_count': 1,
                    'opened_at': 1000,
                    'updated_at': 2000,
                    'closed_at': 2000,
                }]

        class FakeVirtualPositionsReadModel:
            async def enrich_positions(self, *, owner, status, positions):
                return list(positions) + [{
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                    'pool_id': 1,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': owner,
                    'status': 'virtual',
                    'current_liquidity': '5',
                    'position_kind': 'virtual_initial_liquidity',
                    'is_virtual_position': True,
                    'updated_at': 3000,
                    'closed_at': None,
                    'virtual_initial_amount0': '100',
                    'virtual_initial_amount1': '1',
                    'protocol_fee_receiver_account': owner,
                }]

        read_model = PositionsReadModel(
            FakeRepository(),
            virtual_positions_read_model=FakeVirtualPositionsReadModel(),
        )

        result = asyncio.run(read_model.get_positions(owner=owner, status='active'))

        self.assertEqual(len(result['positions']), 1)
        position = result['positions'][0]
        self.assertEqual(position['status'], 'active')
        self.assertEqual(position['current_liquidity'], '0')
        self.assertEqual(position['virtual_current_liquidity'], '5')
        self.assertEqual(position['position_kind'], 'virtual_initial_liquidity')
        self.assertTrue(position['is_virtual_position'])
        self.assertIsNone(position['closed_at'])
        self.assertEqual(position['virtual_initial_amount0'], '100')
        self.assertEqual(position['protocol_fee_receiver_account'], owner)

    def test_positions_read_model_queries_all_before_virtual_filter(self):
        class FakeRepository:
            def get_positions(self, *, owner, status):
                self.calls = (owner, status)
                return []

        class FakeVirtualPositionsReadModel:
            async def enrich_positions(self, *, owner, status, positions):
                self.calls = (owner, status, list(positions))
                return [{'pool_id': 1, 'status': 'virtual'}]

        repository = FakeRepository()
        virtual_positions = FakeVirtualPositionsReadModel()
        read_model = PositionsReadModel(
            repository,
            virtual_positions_read_model=virtual_positions,
        )

        result = asyncio.run(read_model.get_positions(owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', status='virtual'))

        self.assertEqual(repository.calls, ('0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', 'all'))
        self.assertEqual(virtual_positions.calls, ('0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', 'all', []))
        self.assertEqual(result['positions'], [])

    def test_position_metrics_read_model_queries_all_before_virtual_filter(self):
        class FakeRepository:
            def get_positions(self, *, owner, status):
                self.calls = (owner, status)
                return []

        class FakeVirtualPositionsReadModel:
            async def enrich_positions(self, *, owner, status, positions):
                self.calls = (owner, status, list(positions))
                return [{
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                    'pool_id': 1,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': owner,
                    'status': 'virtual',
                    'current_liquidity': '0',
                    'position_kind': 'virtual_initial_liquidity',
                    'is_virtual_position': True,
                    'protocol_fee_receiver_account': owner,
                    'protocol_fee_reference_amount0': '0',
                    'protocol_fee_reference_amount1': '0',
                }]

        async def fake_fetcher(_position):
            raise AssertionError('virtual protocol fee receiver metrics should not call fetcher')

        repository = FakeRepository()
        virtual_positions = FakeVirtualPositionsReadModel()
        read_model = PositionMetricsReadModel(
            repository,
            fake_fetcher,
            virtual_positions_read_model=virtual_positions,
        )

        result = asyncio.run(read_model.get_position_metrics(
            owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
            status='virtual',
        ))

        self.assertEqual(repository.calls, ('0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', 'all'))
        self.assertEqual(
            virtual_positions.calls,
            ('0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', 'virtual', []),
        )
        self.assertEqual(result.metrics[0]['status'], 'virtual')

    def test_position_metrics_read_model_enriches_virtual_positions_when_available(self):
        class FakeRepository:
            def get_positions(self, *, owner, status):
                return []

        class FakeVirtualPositionsReadModel:
            async def enrich_positions(self, *, owner, status, positions):
                self.calls = (owner, status, list(positions))
                return [{
                    'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                    'pool_id': 1,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': owner,
                    'status': 'active',
                    'current_liquidity': '5',
                    'added_liquidity': '5',
                    'removed_liquidity': '0',
                    'add_tx_count': 1,
                    'remove_tx_count': 0,
                    'opened_at': None,
                    'updated_at': 0,
                    'closed_at': None,
                    'position_kind': 'virtual_initial_liquidity',
                    'is_virtual_position': True,
                }]

        async def fake_fetcher(position):
            self.assertEqual(position['pool_application'], '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain')
            self.assertEqual(position['pool_id'], 1)
            return {
                'position_liquidity': '5',
                'current_total_supply': '10',
                'exact_share_ratio': '0.5',
                'redeemable_amount0': '50',
                'redeemable_amount1': '60',
                'virtual_initial_liquidity': True,
                'metrics_status': 'partial_projected_redeemable_only',
                'fee_calculation_complete': False,
                'principal_calculation_complete': False,
                'computation_blockers': [],
                'principal_amount0': None,
                'principal_amount1': None,
                'fee_amount0': '0',
                'fee_amount1': '0',
                'protocol_fee_amount0': '0',
                'protocol_fee_amount1': '0',
                'value_warning_codes': [],
                'value_warning_message': None,
            }

        virtual_positions = FakeVirtualPositionsReadModel()
        read_model = PositionMetricsReadModel(
            FakeRepository(),
            fake_fetcher,
            virtual_positions_read_model=virtual_positions,
        )

        result = asyncio.run(read_model.get_position_metrics(owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain', status='virtual'))

        self.assertEqual(result.owner, '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain')
        self.assertEqual(len(result.metrics), 1)
        self.assertTrue(result.metrics[0]['virtual_initial_liquidity'])
        self.assertNotIn('owner_receives_protocol_fees', result.metrics[0])
        self.assertNotIn('owner_receives_protocol_fees', result.public_payload()['metrics'][0])
        self.assertNotIn('metrics_status', result.public_payload()['metrics'][0])
        self.assertNotIn('fee_calculation_complete', result.public_payload()['metrics'][0])
        self.assertNotIn('principal_calculation_complete', result.public_payload()['metrics'][0])

    def test_position_metrics_handler_records_snapshot_shadow_and_hides_internal_payload(self):
        class FakeReadModel:
            async def get_position_metrics(self, **_kwargs):
                return PositionMetricsReadResult(
                    owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                    metrics=[
                        {
                            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                            'pool_id': 5,
                            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                            'status': 'active',
                            'metrics_status': 'exact',
                            'fee_calculation_complete': True,
                            'principal_calculation_complete': True,
                            'computation_blockers': [],
                            'value_warning_codes': [],
                        },
                    ],
                    metric_diagnostics=[
                        {
                            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                            'pool_id': 5,
                            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                            'status': 'active',
                            'metrics_status': 'exact',
                            'fee_calculation_complete': True,
                            'principal_calculation_complete': True,
                            'computation_blockers': [],
                            'value_warning_codes': [],
                            'fetch_stage': 'snapshot_fast_path',
                            'fetch_reason_code': 'snapshot_fast_path_hit',
                        },
                    ],
                    shadow_diagnostics=[
                        {
                            'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                            'pool_id': 5,
                            'status': 'active',
                            'fetch_stage': 'snapshot_fast_path',
                            'fetch_reason_code': 'snapshot_fast_path_hit',
                            'metrics_status': 'exact',
                            'fee_calculation_complete': False,
                            'principal_calculation_complete': True,
                            'snapshot_shadow': {
                                'mismatch_codes': [],
                                'readiness': 'financial_semantics_pending',
                                'readiness_reason_codes': ['fee_calculation_incomplete'],
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
            PositionMetricsHandler(FakeReadModel(), recorder).get_position_metrics(
                owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain',
                status='active',
            )
        )

        self.assertEqual(payload['owner'], '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain')
        self.assertNotIn('metrics_status', payload['metrics'][0])
        self.assertNotIn('fee_calculation_complete', payload['metrics'][0])
        self.assertNotIn('principal_calculation_complete', payload['metrics'][0])
        self.assertEqual(recorder.inexact_rows, [])
        self.assertEqual(len(recorder.shadow_rows), 1)
        self.assertEqual(recorder.shadow_rows[0]['pool_id'], 5)
        self.assertEqual(recorder.shadow_rows[0]['fetch_stage'], 'snapshot_fast_path')
        self.assertEqual(recorder.shadow_rows[0]['fetch_reason_code'], 'snapshot_fast_path_hit')
