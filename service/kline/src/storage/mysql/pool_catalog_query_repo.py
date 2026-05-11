
class PoolCatalogQueryRepository:
    def __init__(self, db):
        self.db = db

    def get_pool_catalog(self) -> list[dict]:
        cursor = self.db.fresh_cursor(dictionary=True)
        try:
            cursor.execute(
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
            for row in cursor.fetchall():
                rows.append({
                    'pool_id': int(row['pool_id']),
                    'pool_application': row['pool_application'],
                    'token_0': row['token_0'],
                    'token_1': row['token_1'],
                })
            return rows
        finally:
            cursor.close()
