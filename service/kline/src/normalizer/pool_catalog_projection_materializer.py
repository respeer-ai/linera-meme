class PoolCatalogProjectionMaterializer:
    def __init__(self, *, pool_catalog_projection_repository):
        self.pool_catalog_projection_repository = pool_catalog_projection_repository

    def materialize_events(self, events: list[dict[str, object]]) -> dict[str, object]:
        materialized_count = self.pool_catalog_projection_repository.materialize_events(events)
        return {
            'materialized_count': materialized_count,
        }
