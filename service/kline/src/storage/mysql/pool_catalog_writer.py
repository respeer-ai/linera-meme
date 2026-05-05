from db import build_pool_application_value


class PoolCatalogWriter:
    def __init__(self, db):
        self.db = db

    def upsert_pools(self, pools: list[object]) -> None:
        for pool in pools:
            self.db.cursor.execute(
                f'''
                    INSERT INTO {self.db.pools_table}
                    VALUE (%s, %s, %s, %s) as alias
                    ON DUPLICATE KEY UPDATE
                    pool_application = alias.pool_application,
                    token_0 = alias.token_0,
                    token_1 = alias.token_1
                ''',
                (
                    pool.pool_id,
                    build_pool_application_value(pool),
                    pool.token_0,
                    pool.token_1 if pool.token_1 is not None else 'TLINERA',
                ),
            )
        self.db.connection.commit()
