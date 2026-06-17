from storage.mysql.pool_catalog_projection_repo import PoolCatalogProjectionRepository
from storage.mysql.pool_state_projection_repo import PoolStateProjectionRepository
from storage.mysql.projection_pool_catalog_repo import ProjectionPoolCatalogRepository


class PoolIdentityProjectionRepository:
    NATIVE_TOKEN_SENTINEL = 'TLINERA'
    ZERO_TOKEN_ID = '0000000000000000000000000000000000000000000000000000000000000000'

    def __init__(self, db, *, projection_pool_catalog_repository=None, current_swap_application_id: str | None = None):
        self.db = db
        self.current_swap_application_id = current_swap_application_id
        self.projection_pool_catalog_repository = (
            projection_pool_catalog_repository
            or ProjectionPoolCatalogRepository(
                pool_catalog_projection_repository=PoolCatalogProjectionRepository(
                    db,
                    current_swap_application_id=current_swap_application_id,
                ),
                pool_state_projection_repository=PoolStateProjectionRepository(db),
                current_swap_application_id=current_swap_application_id,
            )
        )

    def resolve_for_read(
        self,
        token_0: str,
        token_1: str,
        *,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> tuple[int, str, str, str, bool]:
        normalized_token_0 = self._normalize_token_id(token_0)
        normalized_token_1 = self._normalize_token_id(token_1)
        if pool_application is not None:
            row = self._load_pool_row_by_application(pool_application)
            if row is None:
                raise Exception('Invalid pool application')
        elif pool_id is None:
            return self.resolve_for_tokens(normalized_token_0, normalized_token_1)
        else:
            row = self._load_pool_row_by_id(int(pool_id))
            if row is None:
                raise Exception(f'Invalid pool application for pool_id: {pool_id}')
        resolved_pool_application = str(row['pool_application'])

        pool_token_0 = self._normalize_token_id(row['token_0'])
        pool_token_1 = self._normalize_token_id(row['token_1'])
        if pool_token_0 == normalized_token_0 and pool_token_1 == normalized_token_1:
            token_reversed = False
        elif pool_token_0 == normalized_token_1 and pool_token_1 == normalized_token_0:
            token_reversed = True
        else:
            raise Exception('Invalid token pair for pool')

        return (
            int(row['pool_id']),
            resolved_pool_application,
            normalized_token_0,
            normalized_token_1,
            token_reversed,
        )

    def resolve_for_tokens(self, token_0: str, token_1: str) -> tuple[int, str, str, str, bool]:
        row = self._load_pool_row_by_tokens(token_0, token_1)
        if row is not None:
            return (int(row['pool_id']), str(row['pool_application']), token_0, token_1, False)
        row = self._load_pool_row_by_tokens(token_1, token_0)
        if row is not None:
            return (int(row['pool_id']), str(row['pool_application']), token_0, token_1, True)
        raise Exception('Invalid token pair')

    def _load_pool_row_by_application(self, pool_application: str) -> dict | None:
        row = None
        for pool in self._list_current_pools():
            if str(pool.get('pool_application')) == pool_application:
                row = pool
                break
        if row is None or row.get('pool_application') is None:
            return None
        return row

    def _load_pool_row_by_id(self, pool_id: int) -> dict | None:
        row = None
        for pool in self._list_current_pools():
            if int(pool['pool_id']) == int(pool_id):
                row = pool
                break
        if row is None or row.get('pool_application') is None:
            return None
        return row

    def _load_pool_row_by_tokens(self, token_0: str, token_1: str) -> dict | None:
        rows = [
            pool for pool in self._list_current_pools()
            if self._normalize_token_id(pool.get('token_0')) == token_0
            and self._normalize_token_id(pool.get('token_1')) == token_1
        ]
        if len(rows) > 1:
            raise Exception('Invalid token pair')
        if not rows:
            return None
        row = rows[0]
        if row.get('pool_application') is None:
            raise Exception('Invalid pool application')
        return row

    def _list_current_pools(self) -> list[dict]:
        if not hasattr(self.projection_pool_catalog_repository, 'list_current_pools'):
            raise Exception('projection read boundary is unavailable')
        return self.projection_pool_catalog_repository.list_current_pools() or []

    def _normalize_token_id(self, token_id: str | None) -> str:
        if token_id in (None, self.ZERO_TOKEN_ID):
            return self.NATIVE_TOKEN_SENTINEL
        return str(token_id)
