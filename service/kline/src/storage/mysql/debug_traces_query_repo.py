from request_trace import deserialize_trace_value


class DebugTracesQueryRepository:
    def __init__(
        self,
        db,
        *,
        value_deserializer=None,
    ):
        self.db = db
        self.value_deserializer = value_deserializer or deserialize_trace_value

    def get_debug_traces(
        self,
        *,
        source: str | None = None,
        component: str | None = None,
        operation: str | None = None,
        owner: str | None = None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        start_at: int | None = None,
        end_at: int | None = None,
        limit: int = 200,
        include_payloads: bool = True,
    ) -> list[dict]:
        cursor = self.db.fresh_cursor(dictionary=True)
        where_clauses = []
        params = []
        if source is not None:
            where_clauses.append('source = %s')
            params.append(source)
        if component is not None:
            where_clauses.append('component = %s')
            params.append(component)
        if operation is not None:
            where_clauses.append('operation = %s')
            params.append(operation)
        if owner is not None:
            where_clauses.append('owner = %s')
            params.append(owner)
        if pool_application is not None:
            where_clauses.append('pool_application = %s')
            params.append(pool_application)
        if pool_id is not None:
            where_clauses.append('pool_id = %s')
            params.append(int(pool_id))
        if start_at is not None:
            where_clauses.append('created_at >= %s')
            params.append(int(start_at))
        if end_at is not None:
            where_clauses.append('created_at <= %s')
            params.append(int(end_at))
        where_sql = ''
        if where_clauses:
            where_sql = 'WHERE ' + ' AND '.join(where_clauses)

        try:
            cursor.execute(
                f'''
                    SELECT
                        trace_id,
                        source,
                        component,
                        operation,
                        target,
                        owner,
                        pool_application,
                        pool_id,
                        request_url,
                        request_payload,
                        response_status,
                        response_body,
                        error,
                        details,
                        created_at
                    FROM {self.db.debug_traces_table}
                    {where_sql}
                    ORDER BY trace_id DESC
                    LIMIT %s
                ''',
                (*params, int(limit)),
            )
            rows = []
            for row in cursor.fetchall():
                request_payload = self.value_deserializer(row.get('request_payload'))
                response_body = self.value_deserializer(row.get('response_body'))
                details = self.value_deserializer(row.get('details'))
                rows.append({
                    'trace_id': int(row['trace_id']),
                    'source': row.get('source'),
                    'component': row.get('component'),
                    'operation': row.get('operation'),
                    'target': row.get('target'),
                    'owner': row.get('owner'),
                    'pool_application': row.get('pool_application'),
                    'pool_id': None if row.get('pool_id') is None else int(row['pool_id']),
                    'request_url': row.get('request_url'),
                    'request_payload': request_payload if include_payloads else None,
                    'response_status': None if row.get('response_status') is None else int(row['response_status']),
                    'response_body': response_body if include_payloads else None,
                    'error': row.get('error'),
                    'details': details if include_payloads else None,
                    'created_at': int(row.get('created_at') or 0),
                })
            return rows
        finally:
            cursor.close()
