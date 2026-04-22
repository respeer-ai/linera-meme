import mysql.connector
from swap import Transaction, Pool
import time
import warnings
import json
from decimal import Decimal
from candle_schema import (
    INTERVAL_BUCKET_MS,
    CandleState,
    CandleUpdate,
    apply_candle_update,
    build_candle_bucket_key,
    get_interval_bucket_ms,
)
from request_trace import deserialize_trace_value, serialize_trace_value


def align_timestamp_to_minute_ms(timestamp: int) -> int:
    return timestamp // 60000 * 60000


def build_kline_points_query(
    table_name: str,
    pool_application: str,
    pool_id: int,
    token_reversed: bool,
    start_at: int,
    end_at: int,
) -> str:
    return f'''
        SELECT transaction_id, created_at, price, volume, quote_volume FROM {table_name}
        WHERE pool_application = "{pool_application}"
        AND pool_id = {pool_id}
        AND token_reversed = {token_reversed}
        AND created_at >= {start_at}
        AND created_at <= {end_at}
        AND transaction_type != 'AddLiquidity'
        AND transaction_type != 'RemoveLiquidity'
        ORDER BY created_at ASC, transaction_id ASC
    '''


def build_expected_bucket_count(start_at: int, end_at: int, interval_ms: int) -> int:
    if end_at < start_at:
        return 0
    return (end_at - start_at) // interval_ms + 1


def build_candle_point_payload(interval: str, bucket_start_ms: int, point: dict, now_ms: int):
    bucket_ms = get_interval_bucket_ms(interval)
    bucket_end_ms = bucket_start_ms + bucket_ms - 1
    base_volume = point['base_volume'] if 'base_volume' in point else point['volume']
    quote_volume = point['quote_volume']

    return {
        'timestamp': bucket_start_ms,
        'bucket_start_ms': bucket_start_ms,
        'bucket_end_ms': bucket_end_ms,
        'is_final': now_ms > bucket_end_ms,
        'open': float(point['open']),
        'high': float(point['high']),
        'low': float(point['low']),
        'close': float(point['close']),
        'base_volume': float(base_volume),
        'quote_volume': float(quote_volume),
    }


def build_empty_candle_point_payload(
    interval: str,
    bucket_start_ms: int,
    close_price: float,
    now_ms: int,
):
    return {
        'timestamp': bucket_start_ms,
        'bucket_start_ms': bucket_start_ms,
        'bucket_end_ms': bucket_start_ms + get_interval_bucket_ms(interval) - 1,
        'is_final': now_ms > bucket_start_ms + get_interval_bucket_ms(interval) - 1,
        'open': float(close_price),
        'high': float(close_price),
        'low': float(close_price),
        'close': float(close_price),
        'base_volume': 0.0,
        'quote_volume': 0.0,
    }


def build_continuous_candle_points(
    interval: str,
    start_bucket_ms: int,
    end_bucket_ms: int,
    points: list[dict],
    previous_close: float | None,
    now_ms: int,
):
    interval_ms = get_interval_bucket_ms(interval)
    points_by_bucket = {
        int(point['bucket_start_ms']): point
        for point in points
    }
    continuous_points = []
    last_close = previous_close

    bucket_start_ms = start_bucket_ms
    while bucket_start_ms <= end_bucket_ms:
        point = points_by_bucket.get(bucket_start_ms)
        bucket_end_ms = bucket_start_ms + interval_ms - 1
        if point is not None:
            continuous_points.append(point)
            last_close = float(point['close'])
        elif last_close is not None and now_ms > bucket_end_ms:
            continuous_points.append(build_empty_candle_point_payload(
                interval=interval,
                bucket_start_ms=bucket_start_ms,
                close_price=last_close,
                now_ms=now_ms,
            ))

        bucket_start_ms += interval_ms

    return continuous_points


def build_kline_log_line(event: str, **fields) -> str:
    parts = [f'[kline] event={event}']
    for key in sorted(fields.keys()):
        parts.append(f'{key}={fields[key]}')
    return ' '.join(parts)


def build_pool_application_value(pool: Pool) -> str:
    return f'{pool.pool_application.chain_id}:{pool.pool_application.owner}'


def build_legacy_pool_application_value(pool_id: int) -> str:
    return f'legacy:{pool_id}'


class Db:
    TRANSACTIONS_RANGE_INDEX = 'idx_transactions_pool_reverse_created_at'
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
        }

        # TODO: use alchemy in feature
        warnings.filterwarnings("ignore", category=UserWarning)

        self.connection = mysql.connector.connect(**self.config)
        self.cursor = self.connection.cursor()

        self.transactions_table = 'transactions'
        self.pools_table = 'pools'
        self.candles_table = 'candles'
        self.maker_events_table = 'maker_events'
        self.diagnostics_table = 'diagnostics'
        self.debug_traces_table = 'debug_traces'
        self.debug_storage_degraded_tables = set()

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

        if self.pools_table not in tables:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.pools_table} (
                    pool_id INT UNSIGNED,
                    pool_application VARCHAR(256),
                    token_0 VARCHAR(256),
                    token_1 VARCHAR(256),
                    PRIMARY KEY (pool_id)
                )
            ''')
            self.connection.commit()

        if self.transactions_table not in tables:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.transactions_table} (
                    pool_application VARCHAR(256),
                    pool_id INT UNSIGNED,
                    transaction_id INT UNSIGNED,
                    transaction_type VARCHAR(32),
                    from_account VARCHAR(256),
                    amount_0_in DECIMAL(30, 18),
                    amount_0_out DECIMAL(30, 18),
                    amount_1_in DECIMAL(30, 18),
                    amount_1_out DECIMAL(30, 18),
                    liquidity DECIMAL(30, 18),
                    price DECIMAL(30, 18),
                    volume DECIMAL(30, 18),
                    quote_volume DECIMAL(30, 18),
                    direction VARCHAR(8),
                    token_reversed TINYINT,
                    created_at BIGINT UNSIGNED,
                    PRIMARY KEY (pool_application, pool_id, transaction_id, token_reversed)
                )
            ''')
            self.connection.commit()

        if self.candles_table not in tables:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.candles_table} (
                    pool_application VARCHAR(256),
                    pool_id INT UNSIGNED,
                    token_reversed TINYINT,
                    interval_name VARCHAR(16),
                    bucket_start_ms BIGINT UNSIGNED,
                    open DECIMAL(30, 18),
                    high DECIMAL(30, 18),
                    low DECIMAL(30, 18),
                    close DECIMAL(30, 18),
                    volume DECIMAL(30, 18),
                    quote_volume DECIMAL(30, 18),
                    trade_count INT UNSIGNED,
                    first_trade_id INT UNSIGNED,
                    last_trade_id INT UNSIGNED,
                    first_trade_at_ms BIGINT UNSIGNED,
                    last_trade_at_ms BIGINT UNSIGNED,
                    PRIMARY KEY (pool_application, pool_id, token_reversed, interval_name, bucket_start_ms)
                )
            ''')
            self.connection.commit()

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

        self.ensure_kline_identity_columns()
        self.ensure_transactions_indexes()
        self.ensure_debug_indexes()
        self.ensure_kline_columns()

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

    def resolve_pool_for_write(self, pool: Pool | int):
        if hasattr(pool, 'pool_application'):
            return pool, build_pool_application_value(pool)

        pool_id = int(pool)
        self.cursor.execute(
            f'SELECT pool_application, token_0, token_1 FROM {self.pools_table} WHERE pool_id = %s',
            (pool_id,),
        )
        row = self.cursor.fetchone()
        if row is None:
            raise Exception(f'Unknown pool_id: {pool_id}')

        pool_application, token_0, token_1 = row
        if pool_application is None:
            raise Exception(f'Invalid pool application for pool_id: {pool_id}')

        pool_stub = type('PoolStub', (), {})()
        pool_stub.pool_id = pool_id
        pool_stub.token_0 = token_0
        pool_stub.token_1 = token_1
        pool_stub.pool_application = type('PoolApplicationStub', (), {})()
        pool_stub.pool_application.chain_id, pool_stub.pool_application.owner = pool_application.split(':', 1)
        return pool_stub, pool_application

    def resolve_pool_application(self, pool_id: int, pool_application: str | None = None) -> str:
        if pool_application is not None:
            return pool_application

        self.cursor.execute(
            f'SELECT pool_application FROM {self.pools_table} WHERE pool_id = %s',
            (pool_id,),
        )
        row = self.cursor.fetchone()
        if row is None or row[0] is None:
            raise Exception(f'Invalid pool application for pool_id: {pool_id}')
        return row[0]

    def resolve_pool_identity_for_read(
        self,
        token_0: str,
        token_1: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> (int, str, str, str, bool):
        token_1 = token_1 if token_1 is not None else 'TLINERA'
        token_0 = token_0 if token_0 is not None else 'TLINERA'

        if pool_id is None:
            return self.get_pool_identity(token_0, token_1)

        pool_stub, resolved_pool_application = self.resolve_pool_for_write(pool_id)
        if pool_application is not None and resolved_pool_application != pool_application:
            raise Exception('Invalid pool application')

        pool_token_0 = pool_stub.token_0 if pool_stub.token_0 is not None else 'TLINERA'
        pool_token_1 = pool_stub.token_1 if pool_stub.token_1 is not None else 'TLINERA'
        if pool_token_0 == token_0 and pool_token_1 == token_1:
            token_reversed = False
        elif pool_token_0 == token_1 and pool_token_1 == token_0:
            token_reversed = True
        else:
            raise Exception('Invalid token pair for pool')

        return (int(pool_stub.pool_id), resolved_pool_application, token_0, token_1, token_reversed)

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

        self.cursor.execute(
            f'CREATE INDEX {index_name} ON {table_name} ({", ".join(expected_columns)})'
        )
        self.connection.commit()

    def backfill_legacy_pool_application(self):
        legacy_pool_application = f'CONCAT("legacy:", pool_id)'
        self.cursor.execute(
            f'UPDATE {self.pools_table} SET pool_application = {legacy_pool_application} WHERE pool_application IS NULL'
        )
        self.cursor.execute(
            f'UPDATE {self.transactions_table} SET pool_application = {legacy_pool_application} WHERE pool_application IS NULL'
        )
        self.cursor.execute(
            f'UPDATE {self.candles_table} SET pool_application = {legacy_pool_application} WHERE pool_application IS NULL'
        )
        self.connection.commit()

    def ensure_kline_identity_columns(self):
        self.ensure_column(
            self.pools_table,
            'pool_application',
            'VARCHAR(256) NULL AFTER pool_id',
        )
        self.ensure_column(
            self.transactions_table,
            'pool_application',
            'VARCHAR(256) NULL FIRST',
        )
        self.ensure_column(
            self.candles_table,
            'pool_application',
            'VARCHAR(256) NULL FIRST',
        )

        self.backfill_legacy_pool_application()
        self.ensure_non_null_column(self.transactions_table, 'pool_application', 'VARCHAR(256)')
        self.ensure_non_null_column(self.candles_table, 'pool_application', 'VARCHAR(256)')

        self.ensure_primary_key(
            self.transactions_table,
            ('pool_application', 'pool_id', 'transaction_id', 'token_reversed'),
        )
        self.ensure_primary_key(
            self.candles_table,
            ('pool_application', 'pool_id', 'token_reversed', 'interval_name', 'bucket_start_ms'),
        )

    def ensure_transactions_indexes(self):
        self.ensure_index(
            self.transactions_table,
            self.TRANSACTIONS_RANGE_INDEX,
            ('pool_application', 'pool_id', 'token_reversed', 'created_at'),
        )

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

    def ensure_kline_columns(self):
        self.cursor.execute(f'SHOW COLUMNS FROM {self.transactions_table}')
        transaction_columns = {row[0] for row in self.cursor.fetchall()}
        if 'quote_volume' not in transaction_columns:
            self.cursor.execute(
                f'ALTER TABLE {self.transactions_table} ADD COLUMN quote_volume DECIMAL(30, 18) NULL AFTER volume'
            )
            self.connection.commit()

        self.cursor.execute(f'SHOW COLUMNS FROM {self.candles_table}')
        candle_columns = {row[0] for row in self.cursor.fetchall()}
        if 'quote_volume' not in candle_columns:
            self.cursor.execute(
                f'ALTER TABLE {self.candles_table} ADD COLUMN quote_volume DECIMAL(30, 18) NULL AFTER volume'
            )
            self.connection.commit()

        self.cursor.execute(
            f'''
                UPDATE {self.transactions_table}
                SET quote_volume = price * volume
                WHERE quote_volume IS NULL
                AND transaction_type IN ('BuyToken0', 'SellToken0')
            '''
        )
        self.connection.commit()


    def new_pools(self, pools: list[Pool]):
        for pool in pools:
            self.cursor.execute(
                f'''
                    INSERT INTO {self.pools_table}
                    VALUE (%s, %s, %s, %s) as alias
                    ON DUPLICATE KEY UPDATE
                    pool_application = alias.pool_application,
                    token_0 = alias.token_0,
                    token_1 = alias.token_1
                ''',
                (pool.pool_id,
                 build_pool_application_value(pool),
                 pool.token_0,
                 pool.token_1 if pool.token_1 is not None else 'TLINERA')
            )
        self.connection.commit()

    def new_transaction(self, pool: Pool | int, transaction: Transaction, token_reversed: bool):
        pool, pool_application = self.resolve_pool_for_write(pool)
        direction = transaction.direction(token_reversed)
        base_volume = transaction.base_volume(token_reversed)
        quote_volume = transaction.quote_volume(token_reversed)
        price = transaction.price(token_reversed)
        created_at_ms = transaction.created_at // 1000
        self.cursor.execute(
            f'''
                INSERT IGNORE INTO {self.transactions_table}
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (pool_application,
             pool.pool_id,
             transaction.transaction_id,
             transaction.transaction_type,
             f'{transaction.from_.chain_id}:{transaction.from_.owner}',
             transaction.amount_0_in,
             transaction.amount_0_out,
             transaction.amount_1_in,
             transaction.amount_1_out,
             transaction.liquidity,
             price,
             base_volume,
             quote_volume,
             direction,
             token_reversed,
             created_at_ms)
        )

        was_inserted = self.cursor.rowcount == 1
        if was_inserted:
            self.update_candles_for_transaction(
                pool_application=pool_application,
                pool_id=pool.pool_id,
                transaction=transaction,
                token_reversed=token_reversed,
                created_at_ms=created_at_ms,
                price=price,
                base_volume=base_volume,
                quote_volume=quote_volume,
            )

        return {
            'pool_application': pool_application,
            'pool_id': pool.pool_id,
            'transaction_id': transaction.transaction_id,
            'transaction_type': transaction.transaction_type,
            'from_account': f'{transaction.from_.chain_id}:{transaction.from_.owner}',
            'amount_0_in': transaction.amount_0_in,
            'amount_0_out': transaction.amount_0_out,
            'amount_1_in': transaction.amount_1_in,
            'amount_1_out': transaction.amount_1_out,
            'liquidity': transaction.liquidity,
            'price': price,
            'base_volume': base_volume,
            'quote_volume': quote_volume,
            'direction': direction,
            'token_reversed': token_reversed,
            'created_at': created_at_ms,
        }

    def rebuild_candles_from_transactions(
        self,
        pool_id: int,
        token_reversed: bool,
        interval: str,
        start_at: int,
        end_at: int,
        pool_application: str | None = None,
    ):
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        start_bucket_ms = build_candle_bucket_key(
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=interval,
            created_at_ms=start_at,
        ).bucket_start_ms
        end_bucket_ms = build_candle_bucket_key(
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=interval,
            created_at_ms=end_at,
        ).bucket_start_ms
        query = build_kline_points_query(
            table_name=self.transactions_table,
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            start_at=start_bucket_ms,
            end_at=end_bucket_ms + get_interval_bucket_ms(interval) - 1,
        )
        self.cursor_dict.execute(query)
        rows = self.cursor_dict.fetchall()

        candles_by_bucket = {}
        for row in rows:
            bucket_key = build_candle_bucket_key(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=int(row['created_at']),
            )
            candles_by_bucket[bucket_key.bucket_start_ms] = apply_candle_update(
                existing=candles_by_bucket.get(bucket_key.bucket_start_ms),
                update=CandleUpdate(
                    transaction_id=int(row['transaction_id']),
                    created_at_ms=int(row['created_at']),
                    price=float(row['price']),
                    base_volume=float(row['volume']),
                    quote_volume=float(row['quote_volume']),
                ),
            )

        self.cursor.execute(
            f'''
                DELETE FROM {self.candles_table}
                WHERE pool_application = %s
                AND pool_id = %s
                AND token_reversed = %s
                AND interval_name = %s
                AND bucket_start_ms >= %s
                AND bucket_start_ms <= %s
            ''',
            (pool_application, pool_id, token_reversed, interval, start_bucket_ms, end_bucket_ms),
        )

        for bucket_start_ms in sorted(candles_by_bucket.keys()):
            self.save_candle(
                build_candle_bucket_key(
                    pool_application=pool_application,
                    pool_id=pool_id,
                    token_reversed=token_reversed,
                    interval=interval,
                    created_at_ms=bucket_start_ms,
                ),
                candles_by_bucket[bucket_start_ms],
            )

        self.connection.commit()
        return len(candles_by_bucket)

    def rebuild_pair_candles(self, token_0: str, token_1: str, start_at: int, end_at: int, intervals=None):
        (pool_id, pool_application, token_0, token_1, token_reversed) = self.get_pool_identity(token_0, token_1)
        selected_intervals = list(intervals) if intervals is not None else list(INTERVAL_BUCKET_MS.keys())
        results = {}
        for interval in selected_intervals:
            results[f'{interval}:forward'] = self.rebuild_candles_from_transactions(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                start_at=start_at,
                end_at=end_at,
            )
            results[f'{interval}:reverse'] = self.rebuild_candles_from_transactions(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=not token_reversed,
                interval=interval,
                start_at=start_at,
                end_at=end_at,
            )
        return results

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

    def new_transactions(self, pool: Pool | int, transactions: list[Transaction]):
        _transactions = []

        for transaction in transactions:
            # For each transaction we actually have two direction so we need to create two transactions
            _transactions.append(self.new_transaction(pool, transaction, False))
            if transaction.record_reverse():
                _transactions.append(self.new_transaction(pool, transaction, True))

        self.connection.commit()

        return _transactions

    def load_candle(self, pool_id: int, token_reversed: bool, interval: str, bucket_start_ms: int, pool_application: str | None = None):
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        self.cursor_dict.execute(
            f'''
                SELECT
                    open,
                    high,
                    low,
                    close,
                    volume,
                    quote_volume,
                    trade_count,
                    first_trade_id,
                    last_trade_id,
                    first_trade_at_ms,
                    last_trade_at_ms
                FROM {self.candles_table}
                WHERE pool_application = %s
                AND pool_id = %s
                AND token_reversed = %s
                AND interval_name = %s
                AND bucket_start_ms = %s
            ''',
            (pool_application, pool_id, token_reversed, interval, bucket_start_ms),
        )
        row = self.cursor_dict.fetchone()

        if row is None:
            return None
        if row['quote_volume'] is None:
            candle = self.rebuild_candle_from_transactions(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                bucket_start_ms=bucket_start_ms,
            )
            if candle is None:
                return None

            bucket_key = build_candle_bucket_key(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=bucket_start_ms,
            )
            self.save_candle(bucket_key, candle)
            return candle

        return CandleState(
            open=float(row['open']),
            high=float(row['high']),
            low=float(row['low']),
            close=float(row['close']),
            base_volume=float(row['volume']),
            quote_volume=float(row['quote_volume'] or 0),
            trade_count=int(row['trade_count']),
            first_trade_id=int(row['first_trade_id']),
            last_trade_id=int(row['last_trade_id']),
            first_trade_at_ms=int(row['first_trade_at_ms']),
            last_trade_at_ms=int(row['last_trade_at_ms']),
        )

    def rebuild_candle_from_transactions(
        self,
        pool_id: int,
        token_reversed: bool,
        interval: str,
        bucket_start_ms: int,
        pool_application: str | None = None,
    ):
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        bucket_end_ms = bucket_start_ms + get_interval_bucket_ms(interval) - 1
        query = build_kline_points_query(
            table_name=self.transactions_table,
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            start_at=bucket_start_ms,
            end_at=bucket_end_ms,
        )
        self.cursor_dict.execute(query)
        rows = self.cursor_dict.fetchall()

        candle = None
        for row in rows:
            candle = apply_candle_update(
                existing=candle,
                update=CandleUpdate(
                    transaction_id=int(row['transaction_id']),
                    created_at_ms=int(row['created_at']),
                    price=float(row['price']),
                    base_volume=float(row['volume']),
                    quote_volume=float(row['quote_volume']),
                ),
            )

        return candle

    def save_candle(self, bucket_key, candle: CandleState):
        self.cursor.execute(
            f'''
                INSERT INTO {self.candles_table}
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) as alias
                ON DUPLICATE KEY UPDATE
                open = alias.open,
                high = alias.high,
                low = alias.low,
                close = alias.close,
                volume = alias.volume,
                quote_volume = alias.quote_volume,
                trade_count = alias.trade_count,
                first_trade_id = alias.first_trade_id,
                last_trade_id = alias.last_trade_id,
                first_trade_at_ms = alias.first_trade_at_ms,
                last_trade_at_ms = alias.last_trade_at_ms
            ''',
            (
                bucket_key.pool_application,
                bucket_key.pool_id,
                bucket_key.token_reversed,
                bucket_key.interval,
                bucket_key.bucket_start_ms,
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.base_volume,
                candle.quote_volume,
                candle.trade_count,
                candle.first_trade_id,
                candle.last_trade_id,
                candle.first_trade_at_ms,
                candle.last_trade_at_ms,
            ),
        )

    def get_candle_point(
        self,
        pool_id: int,
        token_reversed: bool,
        interval: str,
        bucket_start_ms: int,
        pool_application: str | None = None,
    ):
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        self.cursor_dict.execute(
            f'''
                SELECT
                    bucket_start_ms,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    quote_volume
                FROM {self.candles_table}
                WHERE pool_application = %s
                AND pool_id = %s
                AND token_reversed = %s
                AND interval_name = %s
                AND bucket_start_ms = %s
            ''',
            (pool_application, pool_id, token_reversed, interval, bucket_start_ms),
        )
        row = self.cursor_dict.fetchone()
        if row is None:
            return None
        if row['quote_volume'] is None:
            return None

        return {
            'timestamp': int(row['bucket_start_ms']),
            'bucket_start_ms': int(row['bucket_start_ms']),
            'bucket_end_ms': int(row['bucket_start_ms']) + get_interval_bucket_ms(interval) - 1,
            'is_final': self.now_ms() > int(row['bucket_start_ms']) + get_interval_bucket_ms(interval) - 1,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'base_volume': float(row['volume']),
            'quote_volume': float(row['quote_volume']),
        }

    def load_previous_candle(
        self,
        pool_id: int,
        token_reversed: bool,
        interval: str,
        before_bucket_start_ms: int,
        pool_application: str | None = None,
    ):
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        self.cursor_dict.execute(
            f'''
                SELECT
                    bucket_start_ms,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    quote_volume,
                    trade_count,
                    first_trade_id,
                    last_trade_id,
                    first_trade_at_ms,
                    last_trade_at_ms
                FROM {self.candles_table}
                WHERE pool_application = %s
                AND pool_id = %s
                AND token_reversed = %s
                AND interval_name = %s
                AND bucket_start_ms < %s
                ORDER BY bucket_start_ms DESC
                LIMIT 1
            ''',
            (pool_application, pool_id, token_reversed, interval, before_bucket_start_ms),
        )
        row = self.cursor_dict.fetchone()

        if row is None:
            return None

        return self.load_candle(
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=interval,
            bucket_start_ms=int(row['bucket_start_ms']),
        )

    def update_candles_for_transaction(
        self,
        pool_id: int,
        transaction: Transaction,
        token_reversed: bool,
        created_at_ms: int,
        price: float,
        base_volume: float,
        quote_volume: float,
        pool_application: str | None = None,
    ):
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        if transaction.transaction_type not in ['BuyToken0', 'SellToken0']:
            return

        update = CandleUpdate(
            transaction_id=transaction.transaction_id,
            created_at_ms=created_at_ms,
            price=float(price),
            base_volume=float(base_volume),
            quote_volume=float(quote_volume),
        )

        for interval in INTERVAL_BUCKET_MS.keys():
            bucket_key = build_candle_bucket_key(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=created_at_ms,
            )
            existing = self.load_candle(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                bucket_start_ms=bucket_key.bucket_start_ms,
            )
            candle = apply_candle_update(existing=existing, update=update)
            self.save_candle(bucket_key, candle)

    def get_pool_identity(self, token_0: str, token_1: str) -> (int, str, str, str, bool):
        token_1 = token_1 if token_1 is not None else 'TLINERA'
        token_0 = token_0 if token_0 is not None else 'TLINERA'

        self.cursor.execute(
            f'''SELECT pool_id, pool_application FROM {self.pools_table}
                WHERE token_0 = "{token_0}"
                AND token_1 = "{token_1}"
            '''
        )
        pool_rows = self.cursor.fetchall()
        if len(pool_rows) > 1:
            raise(Exception('Invalid token pair'))

        token_reversed = False

        if len(pool_rows) == 0:
            self.cursor.execute(
                f'''SELECT pool_id, pool_application FROM {self.pools_table}
                    WHERE token_0 = "{token_1}"
                    AND token_1 = "{token_0}"
                '''
            )
            pool_rows = self.cursor.fetchall()
            token_reversed = True

        if len(pool_rows) != 1:
            raise(Exception('Invalid token pair'))

        pool_id, pool_application = pool_rows[0]
        if pool_application is None:
            raise(Exception('Invalid pool application'))

        return (pool_id, pool_application, token_0, token_1, token_reversed)

    def get_transactions_information(self, token_0: str, token_1: str):
        self.ensure_fresh_read_connection()
        if token_0 is None or token_1 is None:
            query = f'''
                SELECT
                    COUNT(*) AS count,
                    MAX(created_at) AS timestamp_begin,
                    MIN(created_at) AS timestamp_end
                FROM {self.transactions_table}
                JOIN {self.pools_table}
                  ON {self.transactions_table}.pool_id = {self.pools_table}.pool_id
                 AND {self.transactions_table}.pool_application = {self.pools_table}.pool_application
            '''
        else:
            try:
                (pool_id, pool_application, token_0, token_1, token_reversed) = self.get_pool_identity(token_0, token_1)
            except Exception as e:
                print(f'Failed get pool {token_0}:{token_1} -> ERROR {e}')
                return []

            query = f'''
                SELECT
                    COUNT(*) AS count,
                    MAX(created_at) AS timestamp_begin,
                    MIN(created_at) AS timestamp_end
                FROM {self.transactions_table}
                WHERE pool_application = "{pool_application}"
                AND pool_id = {pool_id}
                AND token_reversed = {token_reversed}
            '''

        self.cursor_dict.execute(query)
        return self.cursor_dict.fetchone()

    def get_latest_transaction_watermarks(self):
        self.ensure_fresh_read_connection()
        self.cursor_dict.execute(
            f'''
                SELECT
                    t.pool_id,
                    t.pool_application,
                    MAX(t.created_at) AS max_created_at
                FROM {self.transactions_table} t
                JOIN {self.pools_table} p
                  ON t.pool_id = p.pool_id
                 AND t.pool_application = p.pool_application
                GROUP BY t.pool_id, t.pool_application
            '''
        )
        watermark_rows = self.cursor_dict.fetchall()
        watermarks = {}

        for row in watermark_rows:
            pool_id = int(row['pool_id'])
            pool_application = row['pool_application']
            created_at = int(row['max_created_at'])
            self.cursor_dict.execute(
                f'''
                    SELECT
                        transaction_id,
                        created_at,
                        token_reversed
                    FROM {self.transactions_table}
                    WHERE pool_application = %s
                    AND pool_id = %s
                    AND created_at = %s
                    ORDER BY transaction_id DESC, token_reversed DESC
                    LIMIT 1
                ''',
                (pool_application, pool_id, created_at),
            )
            latest_row = self.cursor_dict.fetchone()
            if latest_row is None:
                continue

            watermarks[(pool_id, *pool_application.split(':', 1))] = (
                int(latest_row['created_at']),
                int(latest_row['transaction_id']),
                1 if bool(latest_row['token_reversed']) else 0,
            )

        return watermarks

    def get_pool_catalog(self):
        self.ensure_fresh_read_connection()
        self.cursor_dict.execute(
            f'''
                SELECT
                    pool_id,
                    pool_application,
                    token_0,
                    token_1
                FROM {self.pools_table}
                ORDER BY pool_id ASC
            '''
        )
        rows = []
        for row in self.cursor_dict.fetchall():
            rows.append({
                'pool_id': int(row['pool_id']),
                'pool_application': row['pool_application'],
                'token_0': row['token_0'],
                'token_1': row['token_1'],
            })
        return rows

    def get_pool_transaction_id_bounds(self, pool_id: int, pool_application: str | None = None):
        self.ensure_fresh_read_connection()
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        self.cursor_dict.execute(
            f'''
                SELECT
                    MIN(transaction_id) AS min_transaction_id,
                    MAX(transaction_id) AS max_transaction_id
                FROM {self.transactions_table}
                WHERE pool_application = %s
                AND pool_id = %s
                AND token_reversed = 0
            ''',
            (pool_application, pool_id),
        )
        row = self.cursor_dict.fetchone()
        if row is None or row['min_transaction_id'] is None or row['max_transaction_id'] is None:
            return None

        return {
            'min_transaction_id': int(row['min_transaction_id']),
            'max_transaction_id': int(row['max_transaction_id']),
        }

    def get_pool_transaction_ids(
        self,
        pool_id: int,
        pool_application: str | None = None,
        start_id: int | None = None,
        end_id: int | None = None,
    ):
        self.ensure_fresh_read_connection()
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        lower_bound = 0 if start_id is None else int(start_id)
        upper_bound = 2 ** 32 - 1 if end_id is None else int(end_id)
        self.cursor_dict.execute(
            f'''
                SELECT transaction_id
                FROM {self.transactions_table}
                WHERE pool_application = %s
                AND pool_id = %s
                AND token_reversed = 0
                AND transaction_id >= %s
                AND transaction_id <= %s
                ORDER BY transaction_id ASC
            ''',
            (pool_application, pool_id, lower_bound, upper_bound),
        )
        return [
            int(row['transaction_id'])
            for row in self.cursor_dict.fetchall()
        ]

    def get_transactions(self, token_0: str, token_1: str, start_at: int, end_at: int):
        self.ensure_fresh_read_connection()
        if token_0 is None or token_1 is None:
            query = f'''
                SELECT t.* FROM {self.transactions_table} t
                JOIN {self.pools_table} p
                  ON t.pool_id = p.pool_id
                 AND t.pool_application = p.pool_application
                WHERE created_at >= {start_at}
                AND created_at <= {end_at}
            '''
        else:
            try:
                (pool_id, pool_application, token_0, token_1, token_reversed) = self.get_pool_identity(token_0, token_1)
            except Exception as e:
                print(f'Failed get pool {token_0}:{token_1} -> ERROR {e}')
                return []

            query = f'''
                SELECT * FROM {self.transactions_table}
                WHERE pool_application = "{pool_application}"
                AND pool_id = {pool_id}
                AND token_reversed = {token_reversed}
                AND created_at >= {start_at}
                AND created_at <= {end_at}
            '''

        self.cursor_dict.execute(query)
        return self.cursor_dict.fetchall()

    def get_positions(self, owner: str, status: str = 'active'):
        self.ensure_fresh_read_connection()
        normalized_status = (status or 'active').lower()
        if normalized_status not in {'active', 'closed', 'all'}:
            raise ValueError('Invalid positions status')

        query_started_at = time.perf_counter()
        query = f'''
            SELECT
                t.pool_application,
                t.pool_id,
                p.token_0,
                p.token_1,
                t.from_account AS owner,
                COALESCE(SUM(CASE
                    WHEN t.transaction_type = 'AddLiquidity' THEN t.liquidity
                    ELSE 0
                END), 0) AS added_liquidity,
                COALESCE(SUM(CASE
                    WHEN t.transaction_type = 'RemoveLiquidity' THEN t.liquidity
                    ELSE 0
                END), 0) AS removed_liquidity,
                COALESCE(SUM(CASE
                    WHEN t.transaction_type = 'AddLiquidity' THEN 1
                    ELSE 0
                END), 0) AS add_tx_count,
                COALESCE(SUM(CASE
                    WHEN t.transaction_type = 'RemoveLiquidity' THEN 1
                    ELSE 0
                END), 0) AS remove_tx_count,
                MIN(CASE
                    WHEN t.transaction_type = 'AddLiquidity' THEN t.created_at
                    ELSE NULL
                END) AS opened_at,
                MAX(t.created_at) AS updated_at
            FROM {self.transactions_table} t
            JOIN {self.pools_table} p
              ON p.pool_id = t.pool_id
             AND p.pool_application = t.pool_application
            WHERE
                t.from_account = %s
                AND t.transaction_type IN ('AddLiquidity', 'RemoveLiquidity')
            GROUP BY
                t.pool_application,
                t.pool_id,
                p.token_0,
                p.token_1,
                t.from_account
        '''
        try:
            self.cursor_dict.execute(query, (owner,))
            rows = self.cursor_dict.fetchall()
        except Exception:
            self._reconnect_read_connection()
            self.cursor_dict.execute(query, (owner,))
            rows = self.cursor_dict.fetchall()
        query_duration_ms = int((time.perf_counter() - query_started_at) * 1000)

        positions = []
        for row in rows:
            added_liquidity = Decimal(str(row['added_liquidity']))
            removed_liquidity = Decimal(str(row['removed_liquidity']))
            current_liquidity = added_liquidity - removed_liquidity
            if abs(current_liquidity) < Decimal('0.000000000001'):
                current_liquidity = Decimal('0')

            position_status = 'active' if current_liquidity > 0 else 'closed'
            if normalized_status != 'all' and position_status != normalized_status:
                continue

            positions.append({
                'pool_application': row['pool_application'],
                'pool_id': int(row['pool_id']),
                'token_0': row['token_0'],
                'token_1': row['token_1'],
                'owner': row['owner'],
                'status': position_status,
                'current_liquidity': self.serialize_decimal(current_liquidity),
                'added_liquidity': self.serialize_decimal(added_liquidity),
                'removed_liquidity': self.serialize_decimal(removed_liquidity),
                'add_tx_count': int(row['add_tx_count']),
                'remove_tx_count': int(row['remove_tx_count']),
                'opened_at': int(row['opened_at']) if row['opened_at'] is not None else None,
                'updated_at': int(row['updated_at']) if row['updated_at'] is not None else None,
                'closed_at': int(row['updated_at']) if position_status == 'closed' and row['updated_at'] is not None else None,
            })

        positions.sort(
            key=lambda row: (
                -(row['closed_at'] if normalized_status == 'closed' else row['updated_at'] or 0),
                row['pool_id'],
            ),
        )
        self.log_positions_event(
            'query',
            duration_ms=query_duration_ms,
            owner=owner,
            row_count=len(positions),
            status=normalized_status,
        )
        return positions

    def get_position_liquidity_history(self, owner: str, pool_application: str, pool_id: int):
        self.ensure_fresh_read_connection()
        self.cursor_dict.execute(
            f'''
                SELECT
                    transaction_id,
                    transaction_type,
                    amount_0_in,
                    amount_0_out,
                    amount_1_in,
                    amount_1_out,
                    liquidity,
                    created_at
                FROM {self.transactions_table}
                WHERE
                    from_account = %s
                    AND pool_application = %s
                    AND pool_id = %s
                    AND transaction_type IN ('AddLiquidity', 'RemoveLiquidity')
                ORDER BY created_at ASC, transaction_id ASC
            ''',
            (owner, pool_application, pool_id),
        )
        return self.cursor_dict.fetchall()

    def get_pool_transaction_history(self, pool_application: str, pool_id: int):
        self.ensure_fresh_read_connection()
        self.cursor_dict.execute(
            f'''
                SELECT
                    transaction_id,
                    transaction_type,
                    from_account,
                    amount_0_in,
                    amount_0_out,
                    amount_1_in,
                    amount_1_out,
                    liquidity,
                    created_at
                FROM {self.transactions_table}
                WHERE
                    pool_application = %s
                    AND pool_id = %s
                    AND token_reversed = 0
                ORDER BY created_at ASC, transaction_id ASC
            ''',
            (pool_application, pool_id),
        )
        return self.cursor_dict.fetchall()

    def get_pool_swap_count_since(
        self,
        pool_application: str,
        pool_id: int,
        created_at: int | None,
    ) -> int:
        self.ensure_fresh_read_connection()
        lower_bound = int(created_at or 0)
        self.cursor_dict.execute(
            f'''
                SELECT COUNT(*) AS swap_count
                FROM {self.transactions_table}
                WHERE
                    pool_application = %s
                    AND pool_id = %s
                    AND created_at >= %s
                    AND transaction_type NOT IN ('AddLiquidity', 'RemoveLiquidity')
            ''',
            (pool_application, pool_id, lower_bound),
        )
        row = self.cursor_dict.fetchone()
        return int(row['swap_count']) if row is not None else 0

    def get_pool_transaction_gap_summary(
        self,
        pool_application: str,
        pool_id: int,
        *,
        start_id: int | None = None,
        end_id: int | None = None,
        sample_limit: int = 8,
    ):
        bounds = self.get_pool_transaction_id_bounds(pool_id, pool_application)
        if bounds is None:
            return {
                'has_internal_gaps': False,
                'start_id': None,
                'end_id': None,
                'missing_count': 0,
                'missing_ids_sample': [],
                'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
            }

        lower_bound = int(bounds['min_transaction_id']) if start_id is None else max(int(start_id), int(bounds['min_transaction_id']))
        upper_bound = int(bounds['max_transaction_id']) if end_id is None else min(int(end_id), int(bounds['max_transaction_id']))
        if lower_bound > upper_bound:
            return {
                'has_internal_gaps': False,
                'start_id': lower_bound,
                'end_id': upper_bound,
                'missing_count': 0,
                'missing_ids_sample': [],
                'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
            }

        return {
            'has_internal_gaps': False,
            'start_id': lower_bound,
            'end_id': upper_bound,
            'missing_count': 0,
            'missing_ids_sample': [],
            'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
        }

    def get_kline_information(self, token_0: str, token_1: str, interval: str, pool_id: int | None = None, pool_application: str | None = None):
        self.ensure_fresh_read_connection()
        (pool_id, pool_application, token_0, token_1, token_reversed) = self.resolve_pool_identity_for_read(
            token_0,
            token_1,
            pool_id=pool_id,
            pool_application=pool_application,
        )

        query = f'''
            SELECT
                COUNT(*) AS count,
                MAX(created_at) AS timestamp_begin,
                MIN(created_at) AS timestamp_end
            FROM {self.transactions_table}
            WHERE pool_application = "{pool_application}"
            AND pool_id = {pool_id}
            AND token_reversed = {token_reversed}
            AND transaction_type != 'AddLiquidity'
            AND transaction_type != 'RemoveLiquidity';
        '''
        self.cursor_dict.execute(query)
        return self.cursor_dict.fetchone()

    def get_kline(self, token_0: str, token_1: str, start_at: int, end_at: int, interval: str, pool_id: int | None = None, pool_application: str | None = None):
        self.ensure_fresh_read_connection()
        request_started_at = time.perf_counter()
        (pool_id, pool_application, token_0, token_1, token_reversed) = self.resolve_pool_identity_for_read(
            token_0,
            token_1,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        interval = interval if interval is not None else '1min'
        self.log_kline_event(
            event='request_start',
            end_at=end_at,
            interval=interval,
            pool_id=pool_id,
            start_at=start_at,
            token_reversed=token_reversed,
        )
        points = self.get_kline_from_candles(
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
        )
        self.log_kline_event(
            event='candles_result',
            interval=interval,
            point_count=len(points),
            pool_id=pool_id,
            token_reversed=token_reversed,
        )

        if len(points) > 0:
            self.log_kline_event(
                event='request_complete',
                duration_ms=int((time.perf_counter() - request_started_at) * 1000),
                interval=interval,
                point_count=len(points),
                pool_id=pool_id,
                source='candles',
                token_reversed=token_reversed,
            )
            return (pool_id, pool_application, token_0, token_1, points)

        self.log_kline_event(
            event='transactions_fallback_start',
            interval=interval,
            pool_id=pool_id,
            token_reversed=token_reversed,
        )
        points = self.get_kline_from_transactions(
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
        )
        self.log_kline_event(
            event='transactions_result',
            interval=interval,
            point_count=len(points),
            pool_id=pool_id,
            token_reversed=token_reversed,
        )
        self.log_kline_event(
            event='request_complete',
            duration_ms=int((time.perf_counter() - request_started_at) * 1000),
            interval=interval,
            point_count=len(points),
            pool_id=pool_id,
            source='transactions',
            token_reversed=token_reversed,
        )

        return (pool_id, pool_application, token_0, token_1, points)

    def get_kline_from_candles(
        self,
        pool_id: int,
        token_reversed: bool,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        interval: str,
        pool_application: str | None = None,
    ):
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        interval = interval if interval is not None else '1min'
        query_start_at = build_candle_bucket_key(
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=interval,
            created_at_ms=start_at,
        ).bucket_start_ms
        query_end_at = build_candle_bucket_key(
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=interval,
            created_at_ms=end_at,
        ).bucket_start_ms

        query_started_at = time.perf_counter()
        self.cursor_dict.execute(
            f'''
                SELECT
                    bucket_start_ms,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    quote_volume
                FROM {self.candles_table}
                WHERE pool_application = %s
                AND pool_id = %s
                AND token_reversed = %s
                AND interval_name = %s
                AND bucket_start_ms >= %s
                AND bucket_start_ms <= %s
                ORDER BY bucket_start_ms ASC
            ''',
            (pool_application, pool_id, token_reversed, interval, query_start_at, query_end_at),
        )
        rows = self.cursor_dict.fetchall()
        query_duration_ms = int((time.perf_counter() - query_started_at) * 1000)
        self.log_kline_event(
            event='candles_query',
            bucket_end_ms=query_end_at,
            bucket_start_ms=query_start_at,
            interval=interval,
            pool_id=pool_id,
            query_ms=query_duration_ms,
            row_count=len(rows),
            token_reversed=token_reversed,
        )
        if len(rows) == 0:
            previous_candle = self.load_previous_candle(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                before_bucket_start_ms=query_start_at,
            )
            if previous_candle is None:
                return []

            return build_continuous_candle_points(
                interval=interval,
                start_bucket_ms=query_start_at,
                end_bucket_ms=query_end_at,
                points=[],
                previous_close=previous_candle.close,
                now_ms=self.now_ms(),
            )

        if any(row.get('quote_volume') is None for row in rows):
            self.log_kline_event(
                event='candles_missing_quote_volume',
                interval=interval,
                pool_id=pool_id,
                row_count=len(rows),
                token_reversed=token_reversed,
            )
            return []

        now_ms = self.now_ms()
        json_data = [
            build_candle_point_payload(
                interval=interval,
                bucket_start_ms=int(row['bucket_start_ms']),
                point=row,
                now_ms=now_ms,
            )
            for row in rows
        ]
        previous_candle = self.load_previous_candle(
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=interval,
            before_bucket_start_ms=query_start_at,
            pool_application=pool_application,
        )

        return build_continuous_candle_points(
            interval=interval,
            start_bucket_ms=query_start_at,
            end_bucket_ms=query_end_at,
            points=json_data,
            previous_close=previous_candle.close if previous_candle is not None else None,
            now_ms=now_ms,
        )

    def get_kline_from_transactions(
        self,
        pool_id: int,
        token_reversed: bool,
        start_at: int,
        end_at: int,
        interval: str,
        pool_application: str | None = None,
    ):
        pool_application = self.resolve_pool_application(pool_id, pool_application)
        query = build_kline_points_query(
            table_name=self.transactions_table,
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            start_at=start_at,
            end_at=end_at,
        )
        query_started_at = time.perf_counter()
        self.cursor_dict.execute(query)
        rows = self.cursor_dict.fetchall()
        query_duration_ms = int((time.perf_counter() - query_started_at) * 1000)
        self.log_kline_event(
            event='transactions_query',
            end_at=end_at,
            interval=interval if interval is not None else '1min',
            pool_id=pool_id,
            query_ms=query_duration_ms,
            row_count=len(rows),
            start_at=start_at,
            token_reversed=token_reversed,
        )
        if len(rows) == 0:
            return []

        interval = interval if interval is not None else '1min'
        now_ms = self.now_ms()
        candle_items = []
        candles_by_bucket = {}

        aggregate_started_at = time.perf_counter()
        for row in rows:
            created_at_ms = int(row['created_at'])
            bucket_key = build_candle_bucket_key(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=created_at_ms,
            )
            update = CandleUpdate(
                transaction_id=int(row['transaction_id']),
                created_at_ms=created_at_ms,
                price=float(row['price']),
                base_volume=float(row['volume']),
                quote_volume=float(row['quote_volume']),
            )
            candle = apply_candle_update(
                existing=candles_by_bucket.get(bucket_key.bucket_start_ms),
                update=update,
            )
            candles_by_bucket[bucket_key.bucket_start_ms] = candle
        aggregate_duration_ms = int((time.perf_counter() - aggregate_started_at) * 1000)

        persist_started_at = time.perf_counter()
        for bucket_start_ms in sorted(candles_by_bucket.keys()):
            bucket_key = build_candle_bucket_key(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=bucket_start_ms,
            )
            candle = candles_by_bucket[bucket_start_ms]
            self.save_candle(bucket_key, candle)
            candle_items.append(build_candle_point_payload(
                interval=interval,
                bucket_start_ms=bucket_start_ms,
                point={
                    'open': candle.open,
                    'high': candle.high,
                    'low': candle.low,
                    'close': candle.close,
                    'base_volume': candle.base_volume,
                    'quote_volume': candle.quote_volume,
                },
                now_ms=now_ms,
            ))

        self.connection.commit()
        persist_duration_ms = int((time.perf_counter() - persist_started_at) * 1000)
        self.log_kline_event(
            event='transactions_materialized',
            aggregate_ms=aggregate_duration_ms,
            bucket_count=len(candles_by_bucket),
            interval=interval,
            persist_ms=persist_duration_ms,
            point_count=len(candle_items),
            pool_id=pool_id,
            row_count=len(rows),
            token_reversed=token_reversed,
        )
        previous_candle = self.load_previous_candle(
            pool_application=pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=interval,
            before_bucket_start_ms=build_candle_bucket_key(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=start_at,
            ).bucket_start_ms,
        )

        return build_continuous_candle_points(
            interval=interval,
            start_bucket_ms=build_candle_bucket_key(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=start_at,
            ).bucket_start_ms,
            end_bucket_ms=build_candle_bucket_key(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=end_at,
            ).bucket_start_ms,
            points=candle_items,
            previous_close=previous_candle.close if previous_candle is not None else None,
            now_ms=now_ms,
        )

    def get_last_kline(self, token_0: str, token_1: str, interval: str, pool_id: int | None = None, pool_application: str | None = None):
        # Only use full minutes data. Only for minute currently
        end_at = time.time() // 60 * 60

        intervals = {
            '1min': 60 * 5,
            '5min': 300 * 3,
            '10min': 600 * 3,
            '1h': 3600 * 3,
            '1D': 86400 * 3,
            '1W': 86400 * 7 * 4,
            '1ME': 86400 * 30 * 12
        }
        interval = interval if interval in intervals else '5min'
        start_at = end_at - intervals[interval]

        start_at *= 1000
        end_at *= 1000

        (pool_id, pool_application, token_0, token_1, points) = self.get_kline(
            token_0,
            token_1,
            start_at,
            end_at,
            interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )

        return  (pool_id, pool_application, token_0, token_1, start_at, end_at, interval, points)

    def get_ticker(self, interval: str):
        self.ensure_fresh_read_connection()
        intervals = {
            "1h": 3600,
            "1d": 86400,
            "1w": 86400 * 7,
            "1m": 86400 * 30,
            "1y": 86400 * 365,
            "all": None
        }

        if interval not in intervals:
            raise Exception('Unsupported interval')

        now = int(time.time())

        if interval == "all":
            start_at = 0
        else:
            start_at = now - intervals[interval]

        end_at = now

        start_at *= 1000
        end_at *= 1000
        token_reversed = False

        query = f'''
            WITH expanded AS (
                SELECT
                    p.token_0 AS token,
                    t.created_at,
                    COALESCE(t.amount_0_in, 0) + COALESCE(t.amount_0_out, 0) AS volume,
                    t.price AS price
                FROM transactions t
                JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                WHERE
                    t.created_at >= {start_at}
                    AND t.created_at <= {end_at}
                    AND t.token_reversed = {token_reversed}
                    AND t.transaction_type IN ('BuyToken0', 'SellToken0')
                UNION ALL
                SELECT
                    p.token_1 AS token,
                    t.created_at,
                    COALESCE(t.amount_1_in, 0) + COALESCE(t.amount_1_out, 0) AS volume,
                    1 / t.price AS price
                FROM transactions t
                JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                WHERE
                    t.created_at >= {start_at}
                    AND t.created_at <= {end_at}
                    AND t.token_reversed = {token_reversed}
                    AND t.transaction_type IN ('BuyToken0', 'SellToken0')
            ),
            token_native_price AS (
                SELECT
                    token,
                    SUBSTRING_INDEX(
                        GROUP_CONCAT(price ORDER BY created_at DESC),
                        ',', 1
                    ) AS price_native
                FROM (
                    SELECT
                        p.token_0 AS token,
                        t.created_at,
                        t.price AS price
                    FROM transactions t
                    JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                    WHERE
                        p.token_1 = 'TLINERA'
                        AND t.token_reversed = {token_reversed}
                    UNION ALL
                    SELECT
                        p.token_1 AS token,
                        t.created_at,
                        1 / t.price AS price
                    FROM transactions t
                    JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                    WHERE
                        p.token_0 = 'TLINERA'
                        AND t.token_reversed = {token_reversed}
                ) x
                GROUP BY token
            ),
            final AS (
                SELECT
                    e.token,
                    e.created_at,
                    e.price,
                    e.volume,
                    np.price_native,
                    e.volume * np.price_native AS volume_native
                FROM expanded e
                LEFT JOIN token_native_price np
                    ON e.token = np.token
            )
            SELECT
                token,
                MAX(price) AS high,
                MIN(price) AS low,
                SUM(volume_native) AS volume,
                COUNT(*) AS tx_count,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(price ORDER BY created_at DESC),
                    ',', 1
                ) AS price_now,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(price ORDER BY created_at ASC),
                    ',', 1
                ) AS price_start
            FROM final
            GROUP BY token
            ORDER BY volume DESC;
        '''
        self.cursor_dict.execute(query)
        return self.cursor_dict.fetchall()

    def get_pool_stats(self, interval: str):
        self.ensure_fresh_read_connection()
        intervals = {
            "1h": 3600,
            "1d": 86400,
            "1w": 86400 * 7,
            "1m": 86400 * 30,
            "1y": 86400 * 365,
            "all": None
        }

        if interval not in intervals:
            raise Exception('Unsupported interval')

        now = int(time.time())

        if interval == "all":
            start_at = 0
        else:
            start_at = now - intervals[interval]

        end_at = now

        start_at *= 1000
        end_at *= 1000
        token_reversed = False

        query = f'''
            SELECT
                p.pool_id,
                p.token_0,
                p.token_1,
                MAX(t.price) AS high,
                MIN(t.price) AS low,
                SUM(COALESCE(t.amount_1_in, 0) + COALESCE(t.amount_1_out, 0)) AS volume,
                COUNT(*) AS tx_count,
                (
                    SELECT t2.price
                    FROM transactions t2
                    WHERE t2.pool_application = p.pool_application
                      AND t2.pool_id = p.pool_id
                      AND t2.created_at >= {start_at}
                      AND t2.created_at <= {end_at}
                      AND t2.transaction_type IN ('BuyToken0', 'SellToken0')
                    ORDER BY t2.created_at DESC
                    LIMIT 1
                ) AS price_now,
                (
                    SELECT t3.price
                    FROM transactions t3
                    WHERE t3.pool_application = p.pool_application
                      AND t3.pool_id = p.pool_id
                      AND t3.created_at >= {start_at}
                      AND t3.created_at <= {end_at}
                      AND t3.transaction_type IN ('BuyToken0', 'SellToken0')
                    ORDER BY t3.created_at ASC
                    LIMIT 1
                ) AS price_start
            FROM transactions t
            JOIN pools p
              ON t.pool_id = p.pool_id
             AND t.pool_application = p.pool_application
            WHERE
                t.created_at >= {start_at}
                AND t.created_at <= {end_at}
                AND t.token_reversed = {token_reversed}
                AND t.transaction_type IN ('BuyToken0', 'SellToken0')
            GROUP BY
                p.pool_id,
                p.token_0,
                p.token_1
            ORDER BY
                volume DESC;
        '''
        try:
            self.cursor_dict.execute(query)
            return self.cursor_dict.fetchall()
        except Exception:
            self._reconnect_read_connection()
            self.cursor_dict.execute(query)
            return self.cursor_dict.fetchall()

    def get_protocol_stats(self, pools: list[Pool]):
        self.ensure_fresh_read_connection()
        from decimal import Decimal
        import time

        intervals = {
            "1h": 3600,
            "1d": 86400,
            "1w": 86400 * 7,
            "1m": 86400 * 30,
            "1y": 86400 * 365,
            "all": None
        }

        interval = '1d'
        now = int(time.time())

        interval_sec = intervals[interval]

        start_at = now - interval_sec
        prev_start_at = start_at - interval_sec
        end_at = now

        # 转 ms
        start_at *= 1000
        prev_start_at *= 1000
        end_at *= 1000

        token_reversed = False

        # =========================
        # ✅ volume（当前 + 上一周期）
        # =========================
        query = f'''
            WITH current AS (
                SELECT
                    SUM(COALESCE(t.amount_1_in, 0) + COALESCE(t.amount_1_out, 0)) AS volume,
                    COUNT(*) AS tx_count
                FROM transactions t
                JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                WHERE
                    t.created_at >= {start_at}
                    AND t.token_reversed = {token_reversed}
            ),
            previous AS (
                SELECT
                    SUM(COALESCE(t.amount_1_in, 0) + COALESCE(t.amount_1_out, 0)) AS volume
                FROM transactions t
                JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                WHERE
                    t.created_at >= {prev_start_at}
                    AND t.created_at < {start_at}
                    AND t.token_reversed = {token_reversed}
            )
            SELECT
                c.volume AS current_volume,
                c.tx_count,
                p.volume AS previous_volume,
                (SELECT COUNT(*) FROM pools) AS pool_count
            FROM current c
            CROSS JOIN previous p;
        '''

        self.cursor_dict.execute(query)
        stats = self.cursor_dict.fetchone()

        current_volume = Decimal(stats["current_volume"] or 0)
        previous_volume = Decimal(stats["previous_volume"] or 0)

        if previous_volume > 0:
            volume_change = (current_volume - previous_volume) / previous_volume
        else:
            volume_change = Decimal(0)

        fees = current_volume * Decimal("0.003")

        # =========================
        # ✅ 当前价格
        # =========================
        price_query_now = f'''
            SELECT
                token,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(price ORDER BY created_at DESC),
                    ',', 1
                ) AS price
            FROM (
                SELECT
                    p.token_0 AS token,
                    t.created_at,
                    t.price AS price
                FROM transactions t
                JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                WHERE
                    p.token_1 = 'TLINERA'
                    AND t.token_reversed = {token_reversed}

                UNION ALL

                SELECT
                    p.token_1 AS token,
                    t.created_at,
                    CASE
                        WHEN t.price IS NULL OR t.price = 0 THEN NULL
                        ELSE 1 / t.price
                    END AS price
                FROM transactions t
                JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                WHERE
                    p.token_0 = 'TLINERA'
                    AND t.token_reversed = {token_reversed}
            ) x
            GROUP BY token;
        '''

        self.cursor_dict.execute(price_query_now)
        prices_now = self.cursor_dict.fetchall()

        price_map_now = {
            row["token"]: Decimal(row["price"]) if row["price"] is not None else Decimal(0)
            for row in prices_now
        }

        # =========================
        # ⚠️ 历史价格（严格限定 24h 前区间）
        # =========================
        price_query_prev = f'''
            SELECT
                token,
                SUBSTRING_INDEX(
                    GROUP_CONCAT(price ORDER BY created_at DESC),
                    ',', 1
                ) AS price
            FROM (
                SELECT
                    p.token_0 AS token,
                    t.created_at,
                    t.price AS price
                FROM transactions t
                JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                WHERE
                    p.token_1 = 'TLINERA'
                    AND t.created_at >= {prev_start_at}
                    AND t.created_at < {start_at}
                    AND t.token_reversed = {token_reversed}

                UNION ALL

                SELECT
                    p.token_1 AS token,
                    t.created_at,
                    CASE
                        WHEN t.price IS NULL OR t.price = 0 THEN NULL
                        ELSE 1 / t.price
                    END AS price
                FROM transactions t
                JOIN pools p ON t.pool_id = p.pool_id AND t.pool_application = p.pool_application
                WHERE
                    p.token_0 = 'TLINERA'
                    AND t.created_at >= {prev_start_at}
                    AND t.created_at < {start_at}
                    AND t.token_reversed = {token_reversed}
            ) x
            GROUP BY token;
        '''

        self.cursor_dict.execute(price_query_prev)
        prices_prev = self.cursor_dict.fetchall()

        price_map_prev = {
            row["token"]: Decimal(row["price"]) if row["price"] is not None else Decimal(0)
            for row in prices_prev
        }

        # =========================
        # ✅ TVL 当前
        # =========================
        tvl_now = Decimal(0)
        tvl_prev = Decimal(0)

        for p in pools:
            reserve0 = Decimal(p.reserve_0)
            reserve1 = Decimal(p.reserve_1)

            price0_now = price_map_now.get(p.token_0, Decimal(0))
            price1_now = price_map_now.get(p.token_1, Decimal(0))

            price0_prev = price_map_prev.get(p.token_0, Decimal(0))
            price1_prev = price_map_prev.get(p.token_1, Decimal(0))

            # ✅ 只计算有价格的 token（避免假跌）
            if price0_now > 0:
                tvl_now += reserve0 * price0_now
            if price1_now > 0:
                tvl_now += reserve1 * price1_now

            if price0_prev > 0:
                tvl_prev += reserve0 * price0_prev
            if price1_prev > 0:
                tvl_prev += reserve1 * price1_prev

        if tvl_prev > 0:
            tvl_change = (tvl_now - tvl_prev) / tvl_prev
        else:
            tvl_change = Decimal(0)

        return {
            "tvl": float(tvl_now),
            "tvl_change": float(tvl_change),
            "volume": float(current_volume),
            "volume_change": float(volume_change),
            "tx_count": stats["tx_count"] or 0,
            "fees": float(fees),
            "pool_count": stats["pool_count"] or 0
        }

    def close(self):
        self.cursor.close()
        self.cursor_dict.close()
        self.connection.close()
