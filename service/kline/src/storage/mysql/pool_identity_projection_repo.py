class PoolIdentityProjectionRepository:
    def __init__(self, db):
        self.db = db

    def resolve_for_read(
        self,
        token_0: str,
        token_1: str,
        *,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> tuple[int, str, str, str, bool]:
        normalized_token_0 = token_0 if token_0 is not None else 'TLINERA'
        normalized_token_1 = token_1 if token_1 is not None else 'TLINERA'
        if pool_id is None:
            return self.resolve_for_tokens(normalized_token_0, normalized_token_1)

        row = self._load_pool_row_by_id(int(pool_id))
        if row is None:
            raise Exception(f'Invalid pool application for pool_id: {pool_id}')
        resolved_pool_application = str(row['pool_application'])
        if pool_application is not None and resolved_pool_application != pool_application:
            raise Exception('Invalid pool application')

        pool_token_0 = row['token_0'] if row['token_0'] is not None else 'TLINERA'
        pool_token_1 = row['token_1'] if row['token_1'] is not None else 'TLINERA'
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

    def _load_pool_row_by_id(self, pool_id: int) -> dict | None:
        self._require_read_boundary()
        self.db.ensure_fresh_read_connection()
        cursor = self.db.cursor_dict
        cursor.execute(
            f'''
            SELECT pool_id, pool_application, token_0, token_1
            FROM {self.db.pools_table}
            WHERE pool_id = %s
            LIMIT 1
            ''',
            (pool_id,),
        )
        row = cursor.fetchone()
        if row is None or row.get('pool_application') is None:
            return None
        return row

    def _load_pool_row_by_tokens(self, token_0: str, token_1: str) -> dict | None:
        self._require_read_boundary()
        self.db.ensure_fresh_read_connection()
        cursor = self.db.cursor_dict
        cursor.execute(
            f'''
            SELECT pool_id, pool_application, token_0, token_1
            FROM {self.db.pools_table}
            WHERE token_0 = %s
              AND token_1 = %s
            ''',
            (token_0, token_1),
        )
        rows = list(cursor.fetchall() or [])
        if len(rows) > 1:
            raise Exception('Invalid token pair')
        if not rows:
            return None
        row = rows[0]
        if row.get('pool_application') is None:
            raise Exception('Invalid pool application')
        return row

    def _require_read_boundary(self) -> None:
        if not hasattr(self.db, 'ensure_fresh_read_connection'):
            raise Exception('projection read boundary is unavailable')
        if not hasattr(self.db, 'cursor_dict'):
            raise Exception('projection read boundary is unavailable')
        if not hasattr(self.db, 'pools_table'):
            raise Exception('projection read boundary is unavailable')
