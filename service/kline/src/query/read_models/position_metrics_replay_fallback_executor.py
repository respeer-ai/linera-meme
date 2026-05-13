class PositionMetricsReplayFallbackExecutor:
    def __init__(
        self,
        *,
        enrich_payload,
        replay_snapshot_shadow_builder,
        replay_fallback_result_builder,
    ):
        self.enrich_payload = enrich_payload
        self.replay_snapshot_shadow_builder = replay_snapshot_shadow_builder
        self.replay_fallback_result_builder = replay_fallback_result_builder

    def execute(
        self,
        *,
        plan,
        fetch_context,
    ):
        fetch_inputs = fetch_context.fetch_inputs()
        payload_result = self.enrich_payload(
            fetch_context.position,
            fetch_context.payload,
            **fetch_inputs.enrich_kwargs(),
        )
        snapshot_shadow = self.replay_snapshot_shadow_builder.build(
            snapshot_inputs=fetch_inputs.snapshot_inputs(),
            position=fetch_context.position,
            projected_metrics=payload_result.metrics,
            replay_summary=fetch_inputs.replay_summary(),
        )
        return self.replay_fallback_result_builder.build(
            projected_metrics=payload_result.metrics,
            snapshot_shadow=snapshot_shadow,
            plan=plan,
        )
