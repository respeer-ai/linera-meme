class PoolMetadataProjectionResolver:
    def __init__(self, *, pool_catalog_projection_repository, pool_state_projection_repository):
        self.pool_catalog_projection_repository = pool_catalog_projection_repository
        self.pool_state_projection_repository = pool_state_projection_repository

    def metadata_by_pool_application(self) -> dict[str, dict]:
        catalog_rows = self.pool_catalog_projection_repository.list_pool_catalog() or []
        state_rows = self.pool_state_projection_repository.list_pool_state_snapshots() or []

        metadata = {}
        for row in catalog_rows:
            pool_application = row.get('pool_application')
            if pool_application in (None, ''):
                continue
            metadata[str(pool_application)] = {
                'pool_id': int(row['pool_id']),
                'token_0': row.get('token_0'),
                'token_1': row.get('token_1'),
            }

        for row in state_rows:
            pool_application = row.get('pool_application_id')
            if pool_application in (None, ''):
                continue
            key = str(pool_application)
            current = metadata.get(key, {})
            created = (row.get('state_payload_json') or {}).get('pool_created_metadata') or {}
            token_0 = created.get('token_0') or current.get('token_0')
            token_1 = created.get('token_1') or current.get('token_1')
            metadata[key] = {
                'pool_id': self._int_or_none(current.get('pool_id')),
                'token_0': token_0,
                'token_1': token_1,
            }

        return metadata

    def metadata_for_pool_application(self, pool_application: str) -> dict | None:
        if pool_application in (None, ''):
            return None
        metadata = self.metadata_by_pool_application()
        return metadata.get(str(pool_application))

    def _int_or_none(self, value):
        if value in (None, ''):
            return None
        return int(value)
