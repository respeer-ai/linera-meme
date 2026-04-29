class ProcessingCursorRepository:
    def __init__(self, connection):
        self.connection = connection
        self.processing_cursors_table = 'processing_cursors'

    def load_cursor(
        self,
        *,
        cursor_name: str,
        partition_key: str,
    ) -> dict | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT
                    cursor_name,
                    cursor_scope,
                    partition_key,
                    last_sequence,
                    last_block_hash,
                    last_success_at,
                    last_attempt_at,
                    status,
                    consecutive_failures,
                    last_error,
                    updated_at
                FROM {self.processing_cursors_table}
                WHERE cursor_name = %s AND partition_key = %s
                ''',
                (cursor_name, partition_key),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            cursor.close()

    def list_cursors(
        self,
        *,
        cursor_scope: str | None = None,
        limit: int = 200,
    ) -> list[dict]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            where_sql = ''
            params: list[object] = []
            if cursor_scope is not None:
                where_sql = 'WHERE cursor_scope = %s'
                params.append(cursor_scope)
            params.append(int(limit))
            cursor.execute(
                f'''
                SELECT
                    cursor_name,
                    cursor_scope,
                    partition_key,
                    last_sequence,
                    last_block_hash,
                    last_success_at,
                    last_attempt_at,
                    status,
                    consecutive_failures,
                    last_error,
                    updated_at
                FROM {self.processing_cursors_table}
                {where_sql}
                ORDER BY updated_at DESC, cursor_name ASC, partition_key ASC
                LIMIT %s
                ''',
                tuple(params),
            )
            return [dict(row) for row in (cursor.fetchall() or [])]
        finally:
            cursor.close()

    def mark_attempt(
        self,
        *,
        cursor_name: str,
        cursor_scope: str,
        partition_key: str,
        last_sequence: str | None,
        last_block_hash: str | None,
    ) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {self.processing_cursors_table}
                (
                    cursor_name,
                    cursor_scope,
                    partition_key,
                    last_sequence,
                    last_block_hash,
                    last_success_at,
                    last_attempt_at,
                    status,
                    consecutive_failures,
                    last_error,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, NULL, UTC_TIMESTAMP(6), %s, 0, NULL, UTC_TIMESTAMP(6))
                ON DUPLICATE KEY UPDATE
                    cursor_scope = VALUES(cursor_scope),
                    last_sequence = VALUES(last_sequence),
                    last_block_hash = VALUES(last_block_hash),
                    last_attempt_at = UTC_TIMESTAMP(6),
                    status = VALUES(status),
                    updated_at = UTC_TIMESTAMP(6)
                ''',
                (
                    cursor_name,
                    cursor_scope,
                    partition_key,
                    last_sequence,
                    last_block_hash,
                    'running',
                ),
            )
            self.connection.commit()
        finally:
            cursor.close()

    def mark_success(
        self,
        *,
        cursor_name: str,
        cursor_scope: str,
        partition_key: str,
        last_sequence: str | None,
        last_block_hash: str | None,
    ) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {self.processing_cursors_table}
                (
                    cursor_name,
                    cursor_scope,
                    partition_key,
                    last_sequence,
                    last_block_hash,
                    last_success_at,
                    last_attempt_at,
                    status,
                    consecutive_failures,
                    last_error,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), %s, 0, NULL, UTC_TIMESTAMP(6))
                ON DUPLICATE KEY UPDATE
                    cursor_scope = VALUES(cursor_scope),
                    last_sequence = VALUES(last_sequence),
                    last_block_hash = VALUES(last_block_hash),
                    last_success_at = UTC_TIMESTAMP(6),
                    last_attempt_at = UTC_TIMESTAMP(6),
                    status = VALUES(status),
                    consecutive_failures = 0,
                    last_error = NULL,
                    updated_at = UTC_TIMESTAMP(6)
                ''',
                (
                    cursor_name,
                    cursor_scope,
                    partition_key,
                    last_sequence,
                    last_block_hash,
                    'ready',
                ),
            )
            self.connection.commit()
        finally:
            cursor.close()

    def mark_failure(
        self,
        *,
        cursor_name: str,
        cursor_scope: str,
        partition_key: str,
        last_sequence: str | None,
        last_block_hash: str | None,
        error_text: str,
    ) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {self.processing_cursors_table}
                (
                    cursor_name,
                    cursor_scope,
                    partition_key,
                    last_sequence,
                    last_block_hash,
                    last_success_at,
                    last_attempt_at,
                    status,
                    consecutive_failures,
                    last_error,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, NULL, UTC_TIMESTAMP(6), %s, 1, %s, UTC_TIMESTAMP(6))
                ON DUPLICATE KEY UPDATE
                    cursor_scope = VALUES(cursor_scope),
                    last_sequence = VALUES(last_sequence),
                    last_block_hash = VALUES(last_block_hash),
                    last_attempt_at = UTC_TIMESTAMP(6),
                    status = VALUES(status),
                    consecutive_failures = consecutive_failures + 1,
                    last_error = VALUES(last_error),
                    updated_at = UTC_TIMESTAMP(6)
                ''',
                (
                    cursor_name,
                    cursor_scope,
                    partition_key,
                    last_sequence,
                    last_block_hash,
                    'error',
                    error_text,
                ),
            )
            self.connection.commit()
        finally:
            cursor.close()

