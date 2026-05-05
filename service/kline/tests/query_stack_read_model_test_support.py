import sys
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport


QueryStackTestSupport.install()


from query.read_models.position_metrics_fetch_coordinator import PositionMetricsFetchCoordinator
from query.read_models.position_metrics_fast_path_executor import PositionMetricsFastPathExecutor
from query.read_models.position_metrics_fast_path_plan_builder import PositionMetricsFastPathPlanBuilder
from query.read_models.position_metrics_projection_payload_adapter import PositionMetricsProjectionPayloadAdapter
from query.read_models.position_metrics_payload_only_executor import PositionMetricsPayloadOnlyExecutor
from query.read_models.position_metrics_replay_fallback_executor import PositionMetricsReplayFallbackExecutor
from query.read_models.position_metrics_replay_bundle import PositionMetricsReplayBundle
from query.read_models.position_metrics_replay_facts import PositionMetricsReplayFacts
from query.read_models.position_metrics_replay_fallback_result_builder import PositionMetricsReplayFallbackResultBuilder
from query.read_models.position_metrics_replay_snapshot_shadow_builder import PositionMetricsReplaySnapshotShadowBuilder
from query.read_models.position_metrics_product_state_query_input_provider import PositionMetricsProductStateQueryInputProvider
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs
from storage.mysql.position_metrics_snapshot_semantic_facts_projector import (
    PositionMetricsSnapshotSemanticFactsProjector,
)
from position_metrics_payload_decision import PositionMetricsPayloadDecision
from position_metrics_payload_result import PositionMetricsPayloadResult


class QueryStackReadModelTestSupport:
    @staticmethod
    def build_live_position_metrics_fetcher(
        *,
        payload_builder=None,
        plan_payload=None,
        enrich_payload,
        query_inputs_loader=None,
        product_state_provider=None,
        snapshot_fast_path=None,
        snapshot_shadow_evaluator=None,
    ):
        if plan_payload is None:
            plan_payload = lambda *_args, **_kwargs: PositionMetricsPayloadResult(
                metrics={'metrics_status': 'partial_live_redeemable_only'},
                decision=PositionMetricsPayloadDecision.PAYLOAD_ONLY,
                reason_code='payload_history_unavailable',
            )
        if payload_builder is None:
            projection_payload_adapter = PositionMetricsProjectionPayloadAdapter()

            async def default_payload_builder(*, position, snapshot_inputs):
                return projection_payload_adapter.build_payload(
                    position=position,
                    snapshot_inputs=snapshot_inputs,
                )

            payload_builder = default_payload_builder
        if query_inputs_loader is None:
            query_inputs_loader = PositionMetricsProductStateQueryInputProvider(
                snapshot_inputs_repository=product_state_provider,
                replay_facts_repository=product_state_provider,
            )
        fetch_coordinator = PositionMetricsFetchCoordinator(
            payload_builder=payload_builder,
            query_input_provider=query_inputs_loader,
            fast_path_plan_builder=PositionMetricsFastPathPlanBuilder(
                snapshot_fast_path=snapshot_fast_path,
            ),
            plan_payload=plan_payload,
            fast_path_executor=PositionMetricsFastPathExecutor(),
            payload_only_executor=PositionMetricsPayloadOnlyExecutor(),
            replay_fallback_executor=PositionMetricsReplayFallbackExecutor(
                enrich_payload=enrich_payload,
                replay_snapshot_shadow_builder=PositionMetricsReplaySnapshotShadowBuilder(
                    snapshot_shadow_evaluator=snapshot_shadow_evaluator,
                ),
                replay_fallback_result_builder=PositionMetricsReplayFallbackResultBuilder(),
            ),
        )

        async def fetch(position: dict):
            return await fetch_coordinator.fetch(position=position)

        return fetch

    @staticmethod
    def recorded_method_names(calls):
        return [call[0] for call in calls]

    @staticmethod
    def replay_summary(
        *,
        latest_position_transaction_id=None,
        latest_position_created_at=None,
        latest_pool_transaction_id=None,
        latest_pool_trade_time_ms=None,
        latest_pool_liquidity_event_time_ms=None,
    ):
        return {
            'latest_position_transaction_id': latest_position_transaction_id,
            'latest_position_created_at': latest_position_created_at,
            'latest_pool_transaction_id': latest_pool_transaction_id,
            'latest_pool_trade_time_ms': latest_pool_trade_time_ms,
            'latest_pool_liquidity_event_time_ms': latest_pool_liquidity_event_time_ms,
        }

    @staticmethod
    def replay_facts(
        *,
        liquidity_history,
        pool_transaction_history,
        pool_swap_count_since_open,
        pool_history_gap_summary,
        replay_summary,
    ):
        return PositionMetricsReplayFacts({
            'liquidity_history': liquidity_history,
            'pool_transaction_history': pool_transaction_history,
            'pool_swap_count_since_open': pool_swap_count_since_open,
            'pool_history_gap_summary': pool_history_gap_summary,
            'replay_summary': replay_summary,
        })

    @staticmethod
    def snapshot_inputs(*, position_basis_snapshot, pool_state_snapshot):
        projected_snapshot = PositionMetricsSnapshotSemanticFactsProjector().project(
            position_basis_snapshot
        )
        return PositionMetricsSnapshotInputs({
            'position_basis_snapshot': projected_snapshot,
            'pool_state_snapshot': pool_state_snapshot,
        })

    @staticmethod
    def build_snapshot_only_repository(snapshot_inputs):
        class SnapshotOnlyRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return snapshot_inputs

            def get_replay_facts(self, **_kwargs):
                raise AssertionError('fast path should not load replay facts')

        return SnapshotOnlyRepository()

    @staticmethod
    def build_query_inputs_loader(product_state_provider):
        return PositionMetricsProductStateQueryInputProvider(
            snapshot_inputs_repository=product_state_provider,
            replay_facts_repository=product_state_provider,
        )

    @staticmethod
    def position_metrics_payload(
        *,
        fee_to,
        total_supply,
        virtual_initial_liquidity,
        liquidity,
        amount0,
        amount1,
    ):
        return {
            'data': {
                'pool': {'fee_to': fee_to},
                'totalSupply': total_supply,
                'virtualInitialLiquidity': virtual_initial_liquidity,
                'liquidity': {
                    'liquidity': liquidity,
                    'amount0': amount0,
                    'amount1': amount1,
                },
            }
        }

    @staticmethod
    def build_payload_builder(payload):
        async def payload_builder(*, position, snapshot_inputs):
            return payload

        return payload_builder
