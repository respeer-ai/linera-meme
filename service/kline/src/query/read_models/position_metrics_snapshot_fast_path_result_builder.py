class PositionMetricsSnapshotFastPathResultBuilder:
    def __init__(
        self,
        *,
        snapshot_shadow_evaluator,
    ):
        self.snapshot_shadow_evaluator = snapshot_shadow_evaluator

    def build(
        self,
        *,
        position: dict,
        live_metrics: dict,
        exact_case: str,
        position_basis_snapshot: dict,
        pool_state_snapshot: dict,
    ) -> dict:
        return {
            'live_metrics': live_metrics,
            'snapshot_shadow': self.snapshot_shadow_evaluator.evaluate_candidate(
                position=position,
                live_metrics=live_metrics,
                exact_case=exact_case,
                position_basis_snapshot=position_basis_snapshot,
                pool_state_snapshot=pool_state_snapshot,
            )
        }
