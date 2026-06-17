from storage.mysql.pool_registry_metadata_repo import PoolRegistryMetadataRepository


class PoolMetadataProjectionResolver:
    def __init__(
        self,
        *,
        pool_catalog_projection_repository,
        pool_state_projection_repository,
        pool_registry_metadata_repository=None,
        current_swap_application_id: str | None = None,
    ):
        self.pool_catalog_projection_repository = pool_catalog_projection_repository
        self.pool_state_projection_repository = pool_state_projection_repository
        self.pool_registry_metadata_repository = pool_registry_metadata_repository
        self.current_swap_application_id = current_swap_application_id

    def metadata_by_pool_application(self) -> dict[str, dict]:
        catalog_rows = self.pool_catalog_projection_repository.list_pool_catalog() or []
        state_rows = self.pool_state_projection_repository.list_pool_state_snapshots() or []
        registry_rows = self._list_registry_pool_metadata()

        metadata = {}
        for row in catalog_rows:
            pool_application = row.get('pool_application')
            if pool_application in (None, ''):
                continue
            metadata[str(pool_application)] = {
                'pool_id': int(row['pool_id']),
                'token_0': row.get('token_0'),
                'token_1': row.get('token_1'),
                'creator_account': row.get('creator_account'),
            }

        for row in registry_rows:
            pool_application = row.get('pool_application')
            if pool_application in (None, ''):
                continue
            current = metadata.get(str(pool_application), {})
            metadata[str(pool_application)] = {
                'pool_id': self._int_or_none(row.get('pool_id')),
                'pool_chain_id': row.get('pool_chain_id') or current.get('pool_chain_id'),
                'token_0': row.get('token_0') or current.get('token_0'),
                'token_1': row.get('token_1') or current.get('token_1'),
                'creator_account': row.get('creator_account') or current.get('creator_account'),
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
                'pool_chain_id': row.get('pool_chain_id') or current.get('pool_chain_id'),
                'token_0': token_0,
                'token_1': token_1,
                'creator_account': current.get('creator_account'),
                'fee_to_account_latest_known': (row.get('state_payload_json') or {}).get('fee_to_account_latest_known'),
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

    def _list_registry_pool_metadata(self) -> list[dict]:
        repository = self.pool_registry_metadata_repository
        if repository is None:
            catalog_db = getattr(self.pool_catalog_projection_repository, 'db', None)
            catalog_connection = getattr(self.pool_catalog_projection_repository, 'connection', None)
            source = catalog_db or catalog_connection
            if source is None:
                return []
            repository = PoolRegistryMetadataRepository(
                source,
                current_swap_application_id=self.current_swap_application_id,
            )
        list_pool_metadata = getattr(repository, 'list_pool_metadata', None)
        if list_pool_metadata is None:
            return []
        return list_pool_metadata() or []
