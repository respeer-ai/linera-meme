
class PoolCatalogQueryRepository:
    def __init__(self, db):
        self.db = db

    def get_pool_catalog(self) -> list[dict]:
        self.db.ensure_fresh_read_connection()
        self.db.cursor_dict.execute(
            f'''
                SELECT
                    pool_id,
                    pool_application,
                    token_0,
                    token_1
                FROM {self.db.pools_table}
                ORDER BY pool_id ASC
            '''
        )
        rows = []
        for row in self.db.cursor_dict.fetchall():
            rows.append({
                'pool_id': int(row['pool_id']),
                'pool_application': row['pool_application'],
                'token_0': row['token_0'],
                'token_1': row['token_1'],
            })
        return rows
