import json


class MakerEventsQueryRepository:
    def __init__(self, db):
        self.db = db

    def get_maker_events(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
        start_at: int,
        end_at: int,
    ) -> list[dict]:
        self.db.ensure_fresh_read_connection()
        if token_0 is None or token_1 is None:
            self.db.cursor_dict.execute(
                f'''
                    SELECT
                        event_id,
                        source,
                        event_type,
                        pool_id,
                        token_0,
                        token_1,
                        amount_0,
                        amount_1,
                        quote_notional,
                        pool_price,
                        details,
                        created_at
                    FROM {self.db.maker_events_table}
                    WHERE created_at >= %s
                    AND created_at <= %s
                    ORDER BY created_at ASC, event_id ASC
                ''',
                (int(start_at), int(end_at)),
            )
        else:
            self.db.cursor_dict.execute(
                f'''
                    SELECT
                        event_id,
                        source,
                        event_type,
                        pool_id,
                        token_0,
                        token_1,
                        amount_0,
                        amount_1,
                        quote_notional,
                        pool_price,
                        details,
                        created_at
                    FROM {self.db.maker_events_table}
                    WHERE token_0 = %s
                    AND token_1 = %s
                    AND created_at >= %s
                    AND created_at <= %s
                    ORDER BY created_at ASC, event_id ASC
                ''',
                (token_0, token_1, int(start_at), int(end_at)),
            )
        rows = []
        for row in self.db.cursor_dict.fetchall():
            rows.append(self._serialize_event_row(row))
        return rows

    def get_maker_events_information(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
    ) -> dict:
        self.db.ensure_fresh_read_connection()
        if token_0 is None or token_1 is None:
            self.db.cursor_dict.execute(
                f'''
                    SELECT
                        COUNT(*) AS count,
                        MAX(created_at) AS timestamp_begin,
                        MIN(created_at) AS timestamp_end
                    FROM {self.db.maker_events_table}
                '''
            )
        else:
            self.db.cursor_dict.execute(
                f'''
                    SELECT
                        COUNT(*) AS count,
                        MAX(created_at) AS timestamp_begin,
                        MIN(created_at) AS timestamp_end
                    FROM {self.db.maker_events_table}
                    WHERE token_0 = %s
                    AND token_1 = %s
                ''',
                (token_0, token_1),
            )
        row = self.db.cursor_dict.fetchone()
        if row is None:
            return {
                'count': 0,
                'timestamp_begin': None,
                'timestamp_end': None,
            }
        return {
            'count': int(row['count'] or 0),
            'timestamp_begin': None if row['timestamp_begin'] is None else int(row['timestamp_begin']),
            'timestamp_end': None if row['timestamp_end'] is None else int(row['timestamp_end']),
        }

    def _serialize_event_row(self, row: dict) -> dict:
        details = row.get('details')
        if isinstance(details, str):
            details = json.loads(details)
        return {
            'event_id': int(row['event_id']),
            'source': row.get('source'),
            'event_type': row.get('event_type'),
            'pool_id': None if row.get('pool_id') is None else int(row['pool_id']),
            'token_0': row.get('token_0'),
            'token_1': row.get('token_1'),
            'amount_0': row.get('amount_0'),
            'amount_1': row.get('amount_1'),
            'quote_notional': row.get('quote_notional'),
            'pool_price': row.get('pool_price'),
            'details': details,
            'created_at': int(row['created_at']),
        }
