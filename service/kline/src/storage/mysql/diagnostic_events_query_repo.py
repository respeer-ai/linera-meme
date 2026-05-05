import json


class DiagnosticEventsQueryRepository:
    def __init__(self, db):
        self.db = db

    def get_diagnostic_events(
        self,
        *,
        source: str | None = None,
        owner: str | None = None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        limit: int = 200,
    ) -> list[dict]:
        self.db.ensure_fresh_read_connection()
        where_clauses = []
        params = []
        if source is not None:
            where_clauses.append('source = %s')
            params.append(source)
        if owner is not None:
            where_clauses.append('owner = %s')
            params.append(owner)
        if pool_application is not None:
            where_clauses.append('pool_application = %s')
            params.append(pool_application)
        if pool_id is not None:
            where_clauses.append('pool_id = %s')
            params.append(int(pool_id))
        where_sql = ''
        if where_clauses:
            where_sql = 'WHERE ' + ' AND '.join(where_clauses)

        self.db.cursor_dict.execute(
            f'''
                SELECT
                    diagnostic_id,
                    source,
                    event_type,
                    severity,
                    owner,
                    pool_application,
                    pool_id,
                    status,
                    details,
                    created_at
                FROM {self.db.diagnostics_table}
                {where_sql}
                ORDER BY diagnostic_id DESC
                LIMIT %s
            ''',
            (*params, int(limit)),
        )
        rows = []
        for row in self.db.cursor_dict.fetchall():
            rows.append({
                'diagnostic_id': int(row['diagnostic_id']),
                'source': row['source'],
                'event_type': row['event_type'],
                'severity': row['severity'],
                'owner': row['owner'],
                'pool_application': row['pool_application'],
                'pool_id': None if row['pool_id'] is None else int(row['pool_id']),
                'status': row['status'],
                'details': None if row['details'] is None else json.loads(row['details']),
                'created_at': int(row['created_at']),
            })
        return rows
