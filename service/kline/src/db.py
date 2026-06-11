import mysql.connector
import time
import warnings
import json
from decimal import Decimal
from account_codec import AccountCodec
from request_trace import deserialize_trace_value, serialize_trace_value


def align_timestamp_to_minute_ms(timestamp: int) -> int:
    return timestamp // 60000 * 60000












def build_kline_log_line(event: str, **fields) -> str:
    parts = [f'[kline] event={event}']
    for key in sorted(fields.keys()):
        parts.append(f'{key}={fields[key]}')
    return ' '.join(parts)






class Db:
    TABLE_FULL_ERRNO = 1114

    def __init__(self, host, port, db_name, username, password, clean_kline):
        self.host = host
        self.db_name = db_name
        self.username = username
        self.password = password
        self.port = port
        self.config = {
            'user': self.username,
            'password': self.password,
            'host': self.host,
            'port': self.port,
            'autocommit': True,
            'raise_on_warnings': False, # TODO: Test with alchemy
            'connection_timeout': 5,
            'read_timeout': 30,
            'write_timeout': 30,
            'use_pure': True,
        }

        # TODO: use alchemy in feature
        warnings.filterwarnings("ignore", category=UserWarning)

        self.connection = mysql.connector.connect(**self.config)
        self.cursor = self.connection.cursor()

        self.maker_events_table = 'maker_events'
        self.diagnostics_table = 'diagnostics'
        self.debug_traces_table = 'debug_traces'
        self.realtime_diagnostics_table = 'realtime_diagnostics'
        self.debug_storage_degraded_tables = set()
        self.debug_retention_ttl_ms = 24 * 60 * 60 * 1000
        self.debug_retention_max_rows = 10_000
        self._debug_retention_cleanup_interval_ms = 60_000
        self._debug_retention_last_cleanup_ms_by_table = {}

        if clean_kline is True:
            self.cursor.execute(f'DROP DATABASE {self.db_name}')
            self.connection.commit()

        self.cursor.execute('SHOW DATABASES')
        databases = [row[0] for row in self.cursor.fetchall()]

        if self.db_name not in databases:
            self.cursor.execute(f'CREATE DATABASE IF NOT EXISTS {self.db_name}')

        self.cursor.close()
        self.connection.close()

        self.config['database'] = self.db_name

        self.connection = mysql.connector.connect(**self.config)
        self.cursor = self.connection.cursor()

        self.cursor.execute('SHOW TABLES')
        tables = [row[0] for row in self.cursor.fetchall()]




        if self.maker_events_table not in tables:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.maker_events_table} (
                    event_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    source VARCHAR(32) NOT NULL,
                    event_type VARCHAR(32) NOT NULL,
                    pool_id INT UNSIGNED,
                    token_0 VARCHAR(256),
                    token_1 VARCHAR(256),
                    amount_0 DECIMAL(30, 18) NULL,
                    amount_1 DECIMAL(30, 18) NULL,
                    quote_notional DECIMAL(30, 18) NULL,
                    pool_price DECIMAL(30, 18) NULL,
                    details TEXT NULL,
                    created_at BIGINT UNSIGNED NOT NULL,
                    PRIMARY KEY (event_id)
                )
            ''')
            self.connection.commit()

        if self.diagnostics_table not in tables:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.diagnostics_table} (
                    diagnostic_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    source VARCHAR(32) NOT NULL,
                    event_type VARCHAR(64) NOT NULL,
                    severity VARCHAR(16) NOT NULL,
                    owner VARCHAR(256) NULL,
                    pool_application VARCHAR(256) NULL,
                    pool_id INT UNSIGNED NULL,
                    status VARCHAR(16) NULL,
                    details TEXT NULL,
                    created_at BIGINT UNSIGNED NOT NULL,
                    PRIMARY KEY (diagnostic_id)
                )
            ''')
            self.connection.commit()

        if self.debug_traces_table not in tables:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.debug_traces_table} (
                    trace_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    source VARCHAR(32) NOT NULL,
                    component VARCHAR(32) NOT NULL,
                    operation VARCHAR(64) NOT NULL,
                    target VARCHAR(64) NOT NULL,
                    owner VARCHAR(256) NULL,
                    pool_application VARCHAR(256) NULL,
                    pool_id INT UNSIGNED NULL,
                    request_url TEXT NOT NULL,
                    request_payload LONGTEXT NULL,
                    response_status INT NULL,
                    response_body LONGTEXT NULL,
                    error TEXT NULL,
                    details LONGTEXT NULL,
                    created_at BIGINT UNSIGNED NOT NULL,
                    PRIMARY KEY (trace_id)
                )
            ''')
            self.connection.commit()

        if self.realtime_diagnostics_table not in tables:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.realtime_diagnostics_table} (
                    realtime_diagnostic_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    stage VARCHAR(64) NOT NULL,
                    event_type VARCHAR(64) NULL,
                    pool_application VARCHAR(256) NULL,
                    pool_id INT UNSIGNED NULL,
                    transaction_id INT UNSIGNED NULL,
                    event_time_ms BIGINT UNSIGNED NULL,
                    queue_lag_ms BIGINT NULL,
                    build_duration_ms BIGINT NULL,
                    notify_duration_ms BIGINT NULL,
                    event_count INT UNSIGNED NULL,
                    kline_payload_count INT UNSIGNED NULL,
                    transaction_payload_count INT UNSIGNED NULL,
                    positions_payload_count INT UNSIGNED NULL,
                    thread_id BIGINT UNSIGNED NULL,
                    details TEXT NULL,
                    created_at BIGINT UNSIGNED NOT NULL,
                    PRIMARY KEY (realtime_diagnostic_id)
                )
            ''')
            self.connection.commit()

        self.ensure_debug_indexes()

        self.cursor_dict = self.connection.cursor(dictionary=True)

    def _reconnect_read_connection(self):
        for cursor_name in ('cursor_dict', 'cursor'):
            cursor = getattr(self, cursor_name, None)
            if cursor is None:
                continue
            try:
                cursor.close()
            except Exception:
                pass

        try:
            self.connection.close()
        except Exception:
            pass

        self.connection = mysql.connector.connect(**self.config)
        self.cursor = self.connection.cursor()
        self.cursor_dict = self.connection.cursor(dictionary=True)

    def now_ms(self):
        return int(time.time() * 1000)

    def ensure_fresh_read_connection(self):
        try:
            self.connection.rollback()
        except Exception:
            self._reconnect_read_connection()
            return

        try:
            self.connection.ping(reconnect=True, attempts=1, delay=0)
        except Exception:
            self._reconnect_read_connection()

    def fresh_cursor(self, *, dictionary: bool = False):
        self.ensure_fresh_read_connection()
        return self.connection.cursor(dictionary=dictionary)

    def log_kline_event(self, event: str, **fields):
        print(build_kline_log_line(event, **fields))

    def log_positions_event(self, event: str, **fields):
        parts = [f'[positions] event={event}']
        for key in sorted(fields.keys()):
            parts.append(f'{key}={fields[key]}')
        print(' '.join(parts))

    def _is_table_full_error(self, error: Exception) -> bool:
        errno = getattr(error, 'errno', None)
        if errno == self.TABLE_FULL_ERRNO:
            return True
        return "is full" in str(error).lower()

    def _mark_debug_storage_degraded(self, *, table_name: str, operation: str, error: Exception):
        if table_name in self.debug_storage_degraded_tables:
            return
        self.debug_storage_degraded_tables.add(table_name)
        self.log_kline_event(
            'debug_storage_degraded',
            table=table_name,
            operation=operation,
            error=str(error),
        )

    def _run_debug_write(self, *, table_name: str, operation: str, callback):
        try:
            self._cleanup_debug_table_if_due(table_name=table_name, reserve_rows=1)
            callback()
            self.connection.commit()
            return True
        except Exception as error:
            if self._is_table_full_error(error):
                self._mark_debug_storage_degraded(
                    table_name=table_name,
                    operation=operation,
                    error=error,
                )
                return False
            raise

    def _cleanup_debug_table_if_due(self, *, table_name: str, reserve_rows: int = 0):
        now_ms = self.now_ms()
        last_cleanup_ms = self._debug_retention_last_cleanup_ms_by_table.get(table_name, 0)
        if now_ms - last_cleanup_ms < self._debug_retention_cleanup_interval_ms:
            return
        self._debug_retention_last_cleanup_ms_by_table[table_name] = now_ms
        self._cleanup_debug_table(table_name=table_name, now_ms=now_ms, reserve_rows=reserve_rows)

    def _cleanup_debug_table(self, *, table_name: str, now_ms: int | None = None, reserve_rows: int = 0):
        id_columns = {
            self.diagnostics_table: 'diagnostic_id',
            self.debug_traces_table: 'trace_id',
            self.realtime_diagnostics_table: 'realtime_diagnostic_id',
        }
        id_column = id_columns.get(table_name)
        if id_column is None:
            return
        effective_now_ms = self.now_ms() if now_ms is None else int(now_ms)
        cutoff_ms = effective_now_ms - self.debug_retention_ttl_ms
        self.cursor.execute(
            f'DELETE FROM {table_name} WHERE created_at < %s',
            (cutoff_ms,),
        )
        self.cursor.execute(f'SELECT COUNT(*) FROM {table_name}')
        row_count = int((self.cursor.fetchone() or [0])[0] or 0)
        max_rows_after_cleanup = max(0, self.debug_retention_max_rows - int(reserve_rows))
        overflow = row_count - max_rows_after_cleanup
        if overflow > 0:
            self.cursor.execute(
                f'''
                    DELETE FROM {table_name}
                    ORDER BY {id_column} ASC
                    LIMIT %s
                ''',
                (overflow,),
            )
        self.connection.commit()

    def cleanup_debug_tables(self):
        now_ms = self.now_ms()
        for table_name in (
            self.diagnostics_table,
            self.debug_traces_table,
            self.realtime_diagnostics_table,
        ):
            self._cleanup_debug_table(table_name=table_name, now_ms=now_ms)

    def record_diagnostic_event(
        self,
        *,
        source: str,
        event_type: str,
        severity: str = 'warning',
        owner: str | None = None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        status: str | None = None,
        details: dict | None = None,
    ):
        self._run_debug_write(
            table_name=self.diagnostics_table,
            operation='insert',
            callback=lambda: self.cursor.execute(
                f'''
                    INSERT INTO {self.diagnostics_table}
                    (source, event_type, severity, owner, pool_application, pool_id, status, details, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    source,
                    event_type,
                    severity,
                    owner,
                    pool_application,
                    None if pool_id is None else int(pool_id),
                    status,
                    None if details is None else json.dumps(details, ensure_ascii=True, sort_keys=True),
                    self.now_ms(),
                ),
            ),
        )

    def get_diagnostic_events(
        self,
        *,
        source: str | None = None,
        owner: str | None = None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        limit: int = 200,
    ):
        self.ensure_fresh_read_connection()
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

        self.cursor_dict.execute(
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
                FROM {self.diagnostics_table}
                {where_sql}
                ORDER BY diagnostic_id DESC
                LIMIT %s
            ''',
            (*params, int(limit)),
        )
        rows = []
        for row in self.cursor_dict.fetchall():
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

    def record_debug_trace(
        self,
        *,
        source: str,
        component: str,
        operation: str,
        target: str,
        request_url: str,
        request_payload,
        response_status: int | None = None,
        response_body=None,
        error: str | None = None,
        owner: str | None = None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        details: dict | None = None,
    ):
        self._run_debug_write(
            table_name=self.debug_traces_table,
            operation='insert',
            callback=lambda: self.cursor.execute(
                f'''
                    INSERT INTO {self.debug_traces_table}
                    (
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
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    source,
                    component,
                    operation,
                    target,
                    owner,
                    pool_application,
                    None if pool_id is None else int(pool_id),
                    request_url,
                    serialize_trace_value(request_payload),
                    None if response_status is None else int(response_status),
                    serialize_trace_value(response_body),
                    error,
                    serialize_trace_value(details),
                    self.now_ms(),
                ),
            ),
        )

    def record_realtime_diagnostic(
        self,
        *,
        stage: str,
        event_type: str | None = None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        transaction_id: int | None = None,
        event_time_ms: int | None = None,
        queue_lag_ms: int | None = None,
        build_duration_ms: int | None = None,
        notify_duration_ms: int | None = None,
        event_count: int | None = None,
        kline_payload_count: int | None = None,
        transaction_payload_count: int | None = None,
        positions_payload_count: int | None = None,
        thread_id: int | None = None,
        details: dict | None = None,
    ):
        self._run_debug_write(
            table_name=self.realtime_diagnostics_table,
            operation='insert',
            callback=lambda: self.cursor.execute(
                f'''
                    INSERT INTO {self.realtime_diagnostics_table}
                    (
                        stage,
                        event_type,
                        pool_application,
                        pool_id,
                        transaction_id,
                        event_time_ms,
                        queue_lag_ms,
                        build_duration_ms,
                        notify_duration_ms,
                        event_count,
                        kline_payload_count,
                        transaction_payload_count,
                        positions_payload_count,
                        thread_id,
                        details,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    stage,
                    event_type,
                    pool_application,
                    None if pool_id is None else int(pool_id),
                    None if transaction_id is None else int(transaction_id),
                    None if event_time_ms is None else int(event_time_ms),
                    None if queue_lag_ms is None else int(queue_lag_ms),
                    None if build_duration_ms is None else int(build_duration_ms),
                    None if notify_duration_ms is None else int(notify_duration_ms),
                    None if event_count is None else int(event_count),
                    None if kline_payload_count is None else int(kline_payload_count),
                    None if transaction_payload_count is None else int(transaction_payload_count),
                    None if positions_payload_count is None else int(positions_payload_count),
                    None if thread_id is None else int(thread_id),
                    None if details is None else json.dumps(details, ensure_ascii=True, sort_keys=True),
                    self.now_ms(),
                ),
            ),
        )

    def get_realtime_diagnostics(
        self,
        *,
        stage: str | None = None,
        event_type: str | None = None,
        pool_application: str | None = None,
        pool_id: int | None = None,
        start_at: int | None = None,
        end_at: int | None = None,
        limit: int = 200,
    ):
        self.ensure_fresh_read_connection()
        where_clauses = []
        params = []
        if stage is not None:
            where_clauses.append('stage = %s')
            params.append(stage)
        if event_type is not None:
            where_clauses.append('event_type = %s')
            params.append(event_type)
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
        self.cursor_dict.execute(
            f'''
                SELECT
                    realtime_diagnostic_id,
                    stage,
                    event_type,
                    pool_application,
                    pool_id,
                    transaction_id,
                    event_time_ms,
                    queue_lag_ms,
                    build_duration_ms,
                    notify_duration_ms,
                    event_count,
                    kline_payload_count,
                    transaction_payload_count,
                    positions_payload_count,
                    thread_id,
                    details,
                    created_at
                FROM {self.realtime_diagnostics_table}
                {where_sql}
                ORDER BY realtime_diagnostic_id DESC
                LIMIT %s
            ''',
            (*params, int(limit)),
        )
        rows = []
        for row in self.cursor_dict.fetchall():
            rows.append({
                'realtime_diagnostic_id': int(row['realtime_diagnostic_id']),
                'stage': row['stage'],
                'event_type': row['event_type'],
                'pool_application': row['pool_application'],
                'pool_id': None if row['pool_id'] is None else int(row['pool_id']),
                'transaction_id': None if row['transaction_id'] is None else int(row['transaction_id']),
                'event_time_ms': None if row['event_time_ms'] is None else int(row['event_time_ms']),
                'queue_lag_ms': None if row['queue_lag_ms'] is None else int(row['queue_lag_ms']),
                'build_duration_ms': None if row['build_duration_ms'] is None else int(row['build_duration_ms']),
                'notify_duration_ms': None if row['notify_duration_ms'] is None else int(row['notify_duration_ms']),
                'event_count': None if row['event_count'] is None else int(row['event_count']),
                'kline_payload_count': None if row['kline_payload_count'] is None else int(row['kline_payload_count']),
                'transaction_payload_count': None if row['transaction_payload_count'] is None else int(row['transaction_payload_count']),
                'positions_payload_count': None if row['positions_payload_count'] is None else int(row['positions_payload_count']),
                'thread_id': None if row['thread_id'] is None else int(row['thread_id']),
                'details': None if row['details'] is None else json.loads(row['details']),
                'created_at': int(row['created_at']),
            })
        return rows

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
    ):
        self.ensure_fresh_read_connection()
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

        self.cursor_dict.execute(
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
                FROM {self.debug_traces_table}
                {where_sql}
                ORDER BY trace_id DESC
                LIMIT %s
            ''',
            (*params, int(limit)),
        )
        rows = []
        for row in self.cursor_dict.fetchall():
            rows.append({
                'trace_id': int(row['trace_id']),
                'source': row['source'],
                'component': row['component'],
                'operation': row['operation'],
                'target': row['target'],
                'owner': row['owner'],
                'pool_application': row['pool_application'],
                'pool_id': None if row['pool_id'] is None else int(row['pool_id']),
                'request_url': row['request_url'],
                'request_payload': deserialize_trace_value(row['request_payload']) if include_payloads else None,
                'response_status': None if row['response_status'] is None else int(row['response_status']),
                'response_body': deserialize_trace_value(row['response_body']) if include_payloads else None,
                'error': row['error'],
                'details': deserialize_trace_value(row['details']) if include_payloads else None,
                'created_at': int(row['created_at']),
            })
        return rows

    def serialize_decimal(self, value):
        if isinstance(value, Decimal):
            return format(value, 'f')
        return value



    def ensure_column(self, table_name: str, column_name: str, definition: str):
        self.cursor.execute(f'SHOW COLUMNS FROM {table_name}')
        existing_columns = {row[0] for row in self.cursor.fetchall()}
        if column_name in existing_columns:
            return

        self.cursor.execute(
            f'ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}'
        )
        self.connection.commit()

    def ensure_non_null_column(self, table_name: str, column_name: str, definition: str):
        self.cursor.execute(f'SHOW COLUMNS FROM {table_name}')
        columns = {row[0]: row for row in self.cursor.fetchall()}
        column = columns.get(column_name)
        if column is not None and len(column) > 2 and column[2] == 'NO':
            return

        self.cursor.execute(
            f'ALTER TABLE {table_name} MODIFY COLUMN {column_name} {definition} NOT NULL'
        )
        self.connection.commit()

    def ensure_primary_key(self, table_name: str, expected_columns: tuple[str, ...]):
        self.cursor.execute(f'SHOW INDEX FROM {table_name}')
        primary_columns = [
            row[4]
            for row in sorted(
                [row for row in self.cursor.fetchall() if len(row) > 4 and row[2] == 'PRIMARY'],
                key=lambda row: row[3],
            )
        ]
        if tuple(primary_columns) == expected_columns:
            return

        if len(primary_columns) > 0:
            self.cursor.execute(f'ALTER TABLE {table_name} DROP PRIMARY KEY')
        self.cursor.execute(
            f'ALTER TABLE {table_name} ADD PRIMARY KEY ({", ".join(expected_columns)})'
        )
        self.connection.commit()

    def ensure_index(self, table_name: str, index_name: str, expected_columns: tuple[str, ...]):
        self.cursor.execute(f'SHOW INDEX FROM {table_name}')
        matching_rows = [
            row for row in self.cursor.fetchall()
            if len(row) > 4 and row[2] == index_name
        ]
        existing_columns = tuple(
            row[4] for row in sorted(matching_rows, key=lambda row: row[3])
        )

        if existing_columns == expected_columns:
            return

        if len(existing_columns) > 0:
            self.cursor.execute(f'DROP INDEX {index_name} ON {table_name}')

        try:
            self.cursor.execute(
                f'CREATE INDEX {index_name} ON {table_name} ({", ".join(expected_columns)})'
            )
        except Exception as exc:
            if getattr(exc, 'errno', None) != 1061:
                raise
        self.connection.commit()

    def ensure_debug_indexes(self):
        index_specs = [
            (
                self.maker_events_table,
                'idx_maker_events_created_event',
                ('created_at', 'event_id'),
            ),
            (
                self.maker_events_table,
                'idx_maker_events_pool_created_event',
                ('pool_id', 'created_at', 'event_id'),
            ),
            (
                self.debug_traces_table,
                'idx_debug_traces_source_component_operation_created_trace',
                ('source', 'component', 'operation', 'created_at', 'trace_id'),
            ),
            (
                self.debug_traces_table,
                'idx_debug_traces_pool_created_trace',
                ('pool_id', 'created_at', 'trace_id'),
            ),
            (
                self.debug_traces_table,
                'idx_debug_traces_owner_created_trace',
                ('owner', 'created_at', 'trace_id'),
            ),
            (
                self.diagnostics_table,
                'idx_diagnostics_pool_created_diag',
                ('pool_id', 'created_at', 'diagnostic_id'),
            ),
            (
                self.diagnostics_table,
                'idx_diagnostics_owner_created_diag',
                ('owner', 'created_at', 'diagnostic_id'),
            ),
            (
                self.realtime_diagnostics_table,
                'idx_realtime_diag_stage_created_id',
                ('stage', 'created_at', 'realtime_diagnostic_id'),
            ),
            (
                self.realtime_diagnostics_table,
                'idx_realtime_diag_pool_created_id',
                ('pool_id', 'created_at', 'realtime_diagnostic_id'),
            ),
        ]
        for table_name, index_name, columns in index_specs:
            try:
                self.ensure_index(table_name, index_name, columns)
            except Exception as error:
                if self._is_table_full_error(error):
                    self._mark_debug_storage_degraded(
                        table_name=table_name,
                        operation=f'create_index:{index_name}',
                        error=error,
                    )
                    continue
                raise

    def new_maker_event(
        self,
        event_type: str,
        pool_id: int,
        token_0: str,
        token_1: str,
        amount_0,
        amount_1,
        quote_notional,
        pool_price,
        details: str,
        created_at: int,
    ):
        self._run_debug_write(
            table_name=self.maker_events_table,
            operation='insert',
            callback=lambda: self.cursor.execute(
                f'''
                    INSERT INTO {self.maker_events_table}
                    (source, event_type, pool_id, token_0, token_1, amount_0, amount_1, quote_notional, pool_price, details, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ''',
                (
                    'maker',
                    event_type,
                    pool_id,
                    token_0,
                    token_1,
                    amount_0,
                    amount_1,
                    quote_notional,
                    pool_price,
                    details,
                    created_at,
                ),
            ),
        )

    def get_maker_events(self, token_0: str, token_1: str, start_at: int, end_at: int):
        self.ensure_fresh_read_connection()
        if token_0 is None or token_1 is None:
            self.cursor_dict.execute(
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
                    FROM {self.maker_events_table}
                    WHERE created_at >= %s
                    AND created_at <= %s
                    ORDER BY created_at ASC, event_id ASC
                ''',
                (start_at, end_at),
            )
            return self.cursor_dict.fetchall()

        self.cursor_dict.execute(
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
                FROM {self.maker_events_table}
                WHERE token_0 = %s
                AND token_1 = %s
                AND created_at >= %s
                AND created_at <= %s
                ORDER BY created_at ASC, event_id ASC
            ''',
            (token_0, token_1, start_at, end_at),
        )
        return self.cursor_dict.fetchall()

    def get_maker_events_information(self, token_0: str, token_1: str):
        self.ensure_fresh_read_connection()
        if token_0 is None or token_1 is None:
            self.cursor_dict.execute(
                f'''
                    SELECT
                        COUNT(*) AS count,
                        MAX(created_at) AS timestamp_begin,
                        MIN(created_at) AS timestamp_end
                    FROM {self.maker_events_table}
                '''
            )
            return self.cursor_dict.fetchone()

        self.cursor_dict.execute(
            f'''
                SELECT
                    COUNT(*) AS count,
                    MAX(created_at) AS timestamp_begin,
                    MIN(created_at) AS timestamp_end
                FROM {self.maker_events_table}
                WHERE token_0 = %s
                AND token_1 = %s
            ''',
            (token_0, token_1),
        )
        return self.cursor_dict.fetchone()




    def close(self):
        self.cursor.close()
        self.cursor_dict.close()
        self.connection.close()
