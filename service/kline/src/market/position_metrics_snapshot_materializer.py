class PositionMetricsSnapshotMaterializer:
    def __init__(
        self,
        *,
        snapshot_builder,
        position_state_snapshot_repository,
        pool_state_snapshot_repository,
    ):
        self.snapshot_builder = snapshot_builder
        self.position_state_snapshot_repository = position_state_snapshot_repository
        self.pool_state_snapshot_repository = pool_state_snapshot_repository

    def materialize_outputs(self, outputs: list[dict[str, object]]) -> dict[str, object]:
        if not outputs:
            return self._summary()
        try:
            plan = self.snapshot_builder.build_materialization_plan(outputs)
            for replacement in plan['position_replacements']:
                self.position_state_snapshot_repository.replace_position_states(
                    owner=replacement['owner'],
                    pool_application_id=replacement['pool_application_id'],
                    states=replacement['states'],
                )
            self.pool_state_snapshot_repository.upsert_pool_states(plan['pool_states'])
            return self._summary(
                affected_pool_count=plan['affected_pool_count'],
                affected_position_count=plan['affected_position_count'],
                persisted_pool_state_count=len(plan['pool_states']),
                persisted_position_state_count=sum(
                    len(replacement['states'])
                    for replacement in plan['position_replacements']
                ),
                degraded=False,
            )
        except Exception as error:
            return self._summary(
                degraded=True,
                error_text=str(error),
            )

    def _summary(
        self,
        *,
        affected_pool_count: int = 0,
        affected_position_count: int = 0,
        persisted_pool_state_count: int = 0,
        persisted_position_state_count: int = 0,
        degraded: bool = False,
        error_text: str | None = None,
    ) -> dict[str, object]:
        return {
            'affected_pool_count': affected_pool_count,
            'affected_position_count': affected_position_count,
            'persisted_pool_state_count': persisted_pool_state_count,
            'persisted_position_state_count': persisted_position_state_count,
            'degraded': degraded,
            'error_text': error_text,
        }
