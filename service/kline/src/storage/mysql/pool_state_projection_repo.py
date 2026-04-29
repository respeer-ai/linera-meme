class PoolStateProjectionRepository:
    def __init__(self, db):
        self.db = db
        self.pool_state_table = 'pool_state_v2'

    def get_pool_state_snapshot(
        self,
        *,
        pool_application_id: str,
    ) -> dict | None:
        if not hasattr(self.db, 'ensure_fresh_read_connection'):
            return None
        if not hasattr(self.db, 'cursor_dict'):
            return None
        self.db.ensure_fresh_read_connection()
        cursor = self.db.cursor_dict
        try:
            cursor.execute(
                f'''
                SELECT *
                FROM {self.pool_state_table}
                WHERE pool_application_id = %s
                LIMIT 1
                ''',
                (pool_application_id,),
            )
            return cursor.fetchone()
        except Exception:
            return None
