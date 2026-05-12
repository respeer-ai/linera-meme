import mysql.connector
from swap import Transaction, Pool
import time
import warnings
import json
from decimal import Decimal
from account_codec import AccountCodec
from legacy_candle_materialization_tool import LegacyCandleMaterializationTool
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
    return AccountCodec().format_account(
        chain_id=pool.pool_application.chain_id,
        owner=pool.pool_application.owner,
    )


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
            'connection_timeout': 5,
            'read_timeout': 30,
            'write_timeout': 30,
            'use_pure': True,
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
        self.realtime_diagnostics_table = 'realtime_diagnostics'
        self.debug_storage_degraded_tables = set()
        self.debug_retention_ttl_ms = 24 * 60 * 60 * 1000
        self.debug_retention_max_rows = 10_000
        self._debug_retention_cleanup_interval_ms = 60_000
        self._debug_retention_last_cleanup_ms_by_table = {}
        self.legacy_candle_materialization_tool = LegacyCandleMaterializationTool(self)

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
        parsed_pool_application = AccountCodec().parse_account(pool_application)
        pool_stub.pool_application.chain_id = parsed_pool_application['chain_id']
        pool_stub.pool_application.owner = parsed_pool_application['owner']
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

        try:
            self.cursor.execute(
                f'CREATE INDEX {index_name} ON {table_name} ({", ".join(expected_columns)})'
            )
        except Exception as exc:
            if getattr(exc, 'errno', None) != 1061:
                raise
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
        from_account = AccountCodec().format_account(
            chain_id=transaction.from_.chain_id,
            owner=transaction.from_.owner,
        )
        self.cursor.execute(
            f'''
                INSERT IGNORE INTO {self.transactions_table}
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ''',
            (pool_application,
             pool.pool_id,
             transaction.transaction_id,
             transaction.transaction_type,
             from_account,
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
            'from_account': from_account,
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
        return self.legacy_candle_materialization_tool.rebuild_pair_candles(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            intervals=intervals,
        )

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
            return None

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

    def has_legacy_candle_bucket(
        self,
        pool_id: int,
        token_reversed: bool,
        interval: str,
        bucket_start_ms: int,
        pool_application: str | None = None,
    ) -> bool:
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
            return False
        return row['quote_volume'] is None

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
            if existing is None and self.has_legacy_candle_bucket(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                bucket_start_ms=bucket_key.bucket_start_ms,
            ):
                self.rebuild_candles_from_transactions(
                    pool_application=pool_application,
                    pool_id=pool_id,
                    token_reversed=token_reversed,
                    interval=interval,
                    start_at=bucket_key.bucket_start_ms,
                    end_at=bucket_key.bucket_start_ms,
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

    def get_kline_information(self, token_0: str, token_1: str, interval: str, pool_id: int | None = None, pool_application: str | None = None):
        return self.legacy_candle_materialization_tool.get_kline_information(
            token_0=token_0,
            token_1=token_1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )

    def get_kline(self, token_0: str, token_1: str, start_at: int, end_at: int, interval: str, pool_id: int | None = None, pool_application: str | None = None):
        return self.legacy_candle_materialization_tool.get_kline(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )

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
        return self.legacy_candle_materialization_tool.get_kline_from_candles(
            pool_id=pool_id,
            token_reversed=token_reversed,
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
            pool_application=pool_application,
        )


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
