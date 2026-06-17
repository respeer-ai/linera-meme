from account_codec import AccountCodec
from storage.mysql.pool_registry_metadata_repo import PoolRegistryMetadataRepository


class ProjectionPoolApplicationRef:
    def __init__(self, pool_application: str):
        parsed = AccountCodec().parse_account(str(pool_application))
        self.chain_id = parsed['chain_id']
        self.owner = parsed['owner']


class ProjectionPoolView:
    def __init__(self, row: dict):
        self.pool_id = int(row['pool_id'])
        self.token_0 = row['token_0']
        self.token_1 = row['token_1']
        self.pool_application = ProjectionPoolApplicationRef(row['pool_application'])
        self.reserve_0 = row.get('current_reserve_0')
        self.reserve_1 = row.get('current_reserve_1')
        self.total_supply = row.get('current_total_supply')
        self.k_last = row.get('current_k_last')
        self.last_trade_time_ms = row.get('last_trade_time_ms')
        self.last_liquidity_event_time_ms = row.get('last_liquidity_event_time_ms')
        self.state_payload_json = row.get('state_payload_json')


class ProjectionPoolCatalogRepository:
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
        self.current_swap_application_id = current_swap_application_id
        self.pool_registry_metadata_repository = (
            pool_registry_metadata_repository
            or self._default_pool_registry_metadata_repository()
        )
        self.account_codec = AccountCodec()

    def _default_pool_registry_metadata_repository(self):
        catalog_db = getattr(self.pool_catalog_projection_repository, 'db', None)
        catalog_connection = getattr(self.pool_catalog_projection_repository, 'connection', None)
        source = catalog_db or catalog_connection
        if source is None:
            return None
        return PoolRegistryMetadataRepository(
            source,
            current_swap_application_id=self.current_swap_application_id,
        )

    def list_current_pools(self) -> list[dict]:
        catalog = self._catalog_rows_by_pool_application()
        state_rows = self.pool_state_projection_repository.list_pool_state_snapshots() or []
        state_by_pool_application = {}
        for row in state_rows:
            pool_application_id = row.get('pool_application_id')
            if pool_application_id is None:
                continue
            pool_application_id_value = str(pool_application_id)
            try:
                self.account_codec.parse_account(pool_application_id_value)
                state_by_pool_application[pool_application_id_value] = row
            except ValueError:
                continue
        pools = []
        for row in catalog.values():
            pool_application = str(row['pool_application'])
            state = state_by_pool_application.get(pool_application)
            token_0, token_1 = self._resolve_tokens(
                catalog_row=row,
                state_row=state or {},
            )
            pools.append({
                'pool_id': int(row['pool_id']),
                'pool_application': pool_application,
                'token_0': token_0,
                'token_1': token_1,
                'current_reserve_0': None if state is None else state.get('current_reserve_0'),
                'current_reserve_1': None if state is None else state.get('current_reserve_1'),
                'current_total_supply': None if state is None else state.get('current_total_supply'),
                'current_k_last': None if state is None else state.get('current_k_last'),
                'last_trade_time_ms': None if state is None else state.get('last_trade_time_ms'),
                'last_liquidity_event_time_ms': None if state is None else state.get('last_liquidity_event_time_ms'),
                'state_payload_json': None if state is None else state.get('state_payload_json'),
            })
        pools.sort(key=lambda pool: (pool['pool_id'], pool['pool_application']))
        return pools

    def list_current_pool_views(self) -> list[ProjectionPoolView]:
        return [ProjectionPoolView(row) for row in self.list_current_pools()]

    def _catalog_rows_by_pool_application(self) -> dict[str, dict]:
        rows = {}
        for row in self.pool_catalog_projection_repository.list_pool_catalog() or []:
            pool_application = row.get('pool_application')
            if pool_application in (None, ''):
                continue
            rows[str(pool_application)] = dict(row)
        for row in self._list_registry_pool_metadata():
            pool_application = row.get('pool_application')
            if pool_application in (None, ''):
                continue
            current = rows.get(str(pool_application), {})
            rows[str(pool_application)] = {
                **current,
                'pool_id': int(row['pool_id']),
                'pool_application': str(pool_application),
                'token_0': row.get('token_0') or current.get('token_0'),
                'token_1': row.get('token_1') or current.get('token_1'),
                'creator_account': row.get('creator_account') or current.get('creator_account'),
            }
        return rows

    def _list_registry_pool_metadata(self) -> list[dict]:
        repository = self.pool_registry_metadata_repository
        if repository is None:
            return []
        list_pool_metadata = getattr(repository, 'list_pool_metadata', None)
        if list_pool_metadata is None:
            return []
        return list_pool_metadata() or []

    def _resolve_tokens(self, *, catalog_row: dict, state_row: dict) -> tuple[str, str]:
        metadata = (state_row.get('state_payload_json') or {}).get('pool_created_metadata') or {}
        token_0 = metadata.get('token_0') or catalog_row.get('token_0')
        token_1 = metadata.get('token_1') or catalog_row.get('token_1')
        return str(token_0), str(token_1)
