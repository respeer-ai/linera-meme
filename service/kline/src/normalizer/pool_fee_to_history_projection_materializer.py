class PoolFeeToHistoryProjectionMaterializer:
    def __init__(self, *, pool_fee_to_history_projection_repository):
        self.pool_fee_to_history_projection_repository = pool_fee_to_history_projection_repository

    def materialize_events(self, events: list[dict[str, object]]) -> dict[str, object]:
        materialized_count = self.pool_fee_to_history_projection_repository.materialize_events(events)
        return {
            'materialized_count': materialized_count,
        }
