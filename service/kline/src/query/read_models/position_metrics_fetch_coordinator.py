import inspect

from query.read_models.position_metrics_fetch_context import PositionMetricsFetchContext
from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult
from query.read_models.position_metrics_fetch_stage import PositionMetricsFetchStage
from query.read_models.position_metrics_fetch_reason_code import PositionMetricsFetchReasonCode


class PositionMetricsFetchCoordinator:
    def __init__(
        self,
        *,
        payload_builder,
        query_input_provider,
        fast_path_plan_builder,
        fast_path_executor,
    ):
        self.payload_builder = payload_builder
        self.query_input_provider = query_input_provider
        self.fast_path_plan_builder = fast_path_plan_builder
        self.fast_path_executor = fast_path_executor

    async def fetch(
        self,
        *,
        position: dict,
    ):
        snapshot_inputs = self.query_input_provider.load_snapshot_inputs(
            position=position,
        )
        if not self._has_materialized_snapshot_inputs(snapshot_inputs):
            return self._snapshot_unavailable_result(position)
        payload = self.payload_builder(
            position=position,
            snapshot_inputs=snapshot_inputs,
        )
        if inspect.isawaitable(payload):
            payload = await payload
        return self.build_result(
            position=position,
            payload=payload,
            snapshot_inputs=snapshot_inputs,
        )

    def build_result(
        self,
        *,
        position: dict,
        payload: dict,
        snapshot_inputs=None,
    ):
        if not self._has_materialized_snapshot_inputs(snapshot_inputs):
            return self._snapshot_unavailable_result(position)
        fetch_context = PositionMetricsFetchContext(
            position=position,
            payload=payload,
            query_input_provider=self.query_input_provider,
            snapshot_inputs=snapshot_inputs,
        )
        plan = self.fast_path_plan_builder.build(fetch_context=fetch_context)
        if plan is None:
            return self._snapshot_unavailable_result(fetch_context.position)
        return self.fast_path_executor.execute(
            plan=plan,
        )

    def _has_materialized_snapshot_inputs(self, snapshot_inputs) -> bool:
        if snapshot_inputs is None:
            return False
        return (
            snapshot_inputs.position_basis_snapshot().raw() is not None
            and snapshot_inputs.pool_state_snapshot().raw() is not None
        )

    def _snapshot_unavailable_result(self, position: dict):
        return PositionMetricsFetchedResult(
            projected_metrics=self._snapshot_unavailable_metrics(position),
            fetch_stage=PositionMetricsFetchStage.SNAPSHOT_UNAVAILABLE,
            fetch_reason_code=PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_NO_FALLBACK,
        )

    def _snapshot_unavailable_metrics(self, position: dict) -> dict:
        return {
            'position_liquidity': position.get('current_liquidity', '0'),
            'current_total_supply': None,
            'exact_share_ratio': None,
            'redeemable_amount0': '0',
            'redeemable_amount1': '0',
            'virtual_initial_liquidity': bool(position.get('is_virtual_position')),
            'metrics_status': 'snapshot_unavailable',
            'fee_calculation_complete': False,
            'principal_calculation_complete': False,
            'owner_receives_protocol_fees': False,
            'computation_blockers': ['missing_position_metrics_snapshot'],
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
            'value_warning_codes': ['snapshot_unavailable'],
            'value_warning_message': 'Position metrics snapshot is not available yet.',
        }

