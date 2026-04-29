class PositionStateProjectionRepository:
    def __init__(self, db):
        self.db = db
        self.position_state_table = 'position_state_v2'

    def get_position_basis_snapshot(
        self,
        *,
        owner: str,
        pool_application_id: str,
        status: str = 'active',
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
                FROM {self.position_state_table}
                WHERE owner = %s
                  AND pool_application_id = %s
                  AND status = %s
                LIMIT 1
                ''',
                (owner, pool_application_id, status),
            )
            return cursor.fetchone()
        except Exception:
            return None
