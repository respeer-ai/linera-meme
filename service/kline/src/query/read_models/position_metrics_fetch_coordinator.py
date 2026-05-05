import inspect

from query.read_models.position_metrics_fetch_context import PositionMetricsFetchContext
from query.read_models.position_metrics_fetch_plan import PositionMetricsFetchPlan


class PositionMetricsFetchCoordinator:
    def __init__(
        self,
        *,
        payload_builder,
        query_input_provider,
        fast_path_plan_builder,
        plan_payload,
        fast_path_executor,
        payload_only_executor,
        replay_fallback_executor,
    ):
        self.payload_builder = payload_builder
        self.query_input_provider = query_input_provider
        self.fast_path_plan_builder = fast_path_plan_builder
        self.plan_payload = plan_payload
        self.fast_path_executor = fast_path_executor
        self.payload_only_executor = payload_only_executor
        self.replay_fallback_executor = replay_fallback_executor

    async def fetch(
        self,
        *,
        position: dict,
    ):
        snapshot_inputs = self.query_input_provider.load_snapshot_inputs(
            position=position,
        )
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
        fetch_context = PositionMetricsFetchContext(
            position=position,
            payload=payload,
            query_input_provider=self.query_input_provider,
            snapshot_inputs=snapshot_inputs,
        )
        plan = self.fast_path_plan_builder.build(fetch_context=fetch_context)
        if plan is None:
            payload_result = self.plan_payload(
                fetch_context.position,
                fetch_context.payload,
            )
            if not payload_result.needs_replay_assembly():
                plan = PositionMetricsFetchPlan.payload_only(payload_result)
            else:
                plan = PositionMetricsFetchPlan.replay_fallback(payload_result)
        if plan.is_snapshot_fast_path():
            return self.fast_path_executor.execute(
                plan=plan,
            )
        if plan.is_payload_only():
            return self.payload_only_executor.execute(
                plan=plan,
            )
        return self.replay_fallback_executor.execute(
            plan=plan,
            fetch_context=fetch_context,
        )
