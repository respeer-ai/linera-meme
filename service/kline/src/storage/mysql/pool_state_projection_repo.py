import json


class PoolStateProjectionRepository:
    def __init__(self, db):
        self.db = db
        self.pool_state_table = 'pool_state_v2'

    def get_pool_state_snapshot(
        self,
        *,
        pool_application_id: str,
    ) -> dict | None:
        cursor = self.db.fresh_cursor(dictionary=True)
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
            return self._decode_row(cursor.fetchone())
        except Exception:
            return None
        finally:
            cursor.close()

    def list_pool_state_snapshots(self) -> list[dict] | None:
        cursor = self.db.fresh_cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT *
                FROM {self.pool_state_table}
                ORDER BY pool_application_id ASC
                '''
            )
            return [
                row
                for row in (self._decode_row(row) for row in (cursor.fetchall() or []))
                if row is not None
            ]
        except Exception:
            return None
        finally:
            cursor.close()

    def _decode_row(self, row: dict | None) -> dict | None:
        if row is None:
            return None
        decoded = dict(row)
        payload = decoded.get('state_payload_json')
        if isinstance(payload, str):
            decoded['state_payload_json'] = json.loads(payload)
        return decoded
