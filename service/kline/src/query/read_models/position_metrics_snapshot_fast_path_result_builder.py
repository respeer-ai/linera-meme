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
        projected_metrics: dict,
        exact_case: str,
        position_basis_snapshot: dict,
        pool_state_snapshot: dict,
    ) -> dict:
        return {
            'projected_metrics': projected_metrics,
            'snapshot_shadow': self.snapshot_shadow_evaluator.evaluate_candidate(
                position=position,
                projected_metrics=projected_metrics,
                exact_case=exact_case,
                position_basis_snapshot=position_basis_snapshot,
                pool_state_snapshot=pool_state_snapshot,
            )
        }
