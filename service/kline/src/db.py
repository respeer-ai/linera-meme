import mysql.connector
from swap import Transaction, Pool
import time
import warnings
from candle_schema import (
    INTERVAL_BUCKET_MS,
    CandleState,
    CandleUpdate,
    apply_candle_update,
    build_candle_bucket_key,
    get_interval_bucket_ms,
)


def align_timestamp_to_minute_ms(timestamp: int) -> int:
    return timestamp // 60000 * 60000


def build_kline_points_query(
    table_name: str,
    pool_id: int,
    token_reversed: bool,
    start_at: int,
    end_at: int,
) -> str:
    return f'''
        SELECT transaction_id, created_at, price, volume, quote_volume FROM {table_name}
        WHERE pool_id = {pool_id}
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


def filter_zero_volume_candles(points: list[dict]):
    return [point for point in points if float(point['base_volume']) > 0]


def build_kline_log_line(event: str, **fields) -> str:
    parts = [f'[kline] event={event}']
    for key in sorted(fields.keys()):
        parts.append(f'{key}={fields[key]}')
    return ' '.join(parts)


class Db:
    TRANSACTIONS_RANGE_INDEX = 'idx_transactions_pool_reverse_created_at'

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
            'raise_on_warnings': False, # TODO: Test with alchemy
        }

        # TODO: use alchemy in feature
        warnings.filterwarnings("ignore", category=UserWarning)

        self.connection = mysql.connector.connect(**self.config)
        self.cursor = self.connection.cursor()

        self.transactions_table = 'transactions'
        self.pools_table = 'pools'
        self.candles_table = 'candles'

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
                    token_0 VARCHAR(256),
                    token_1 VARCHAR(256),
                    PRIMARY KEY (pool_id)
                )
            ''')
            self.connection.commit()

        if self.transactions_table not in tables:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.transactions_table} (
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
                    PRIMARY KEY (pool_id, transaction_id, token_reversed)
                )
            ''')
            self.connection.commit()

        if self.candles_table not in tables:
            self.cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {self.candles_table} (
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
                    PRIMARY KEY (pool_id, token_reversed, interval_name, bucket_start_ms)
                )
            ''')
            self.connection.commit()

        self.ensure_transactions_indexes()
        self.ensure_kline_columns()

        self.cursor_dict = self.connection.cursor(dictionary=True)

    def now_ms(self):
        return int(time.time() * 1000)

    def log_kline_event(self, event: str, **fields):
        print(build_kline_log_line(event, **fields))

    def ensure_transactions_indexes(self):
        self.cursor.execute(f'SHOW INDEX FROM {self.transactions_table}')
        existing_indexes = {
            row[2] for row in self.cursor.fetchall()
            if len(row) > 2 and row[2] is not None
        }

        if self.TRANSACTIONS_RANGE_INDEX not in existing_indexes:
            self.cursor.execute(f'''
                CREATE INDEX {self.TRANSACTIONS_RANGE_INDEX}
                ON {self.transactions_table} (pool_id, token_reversed, created_at)
            ''')
            self.connection.commit()

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
                    VALUE (%s, %s, %s) as alias
                    ON DUPLICATE KEY UPDATE
                    token_0 = alias.token_0,
                    token_1 = alias.token_1
                ''',
                (pool.pool_id,
                 pool.token_0,
                 pool.token_1 if pool.token_1 is not None else 'TLINERA')
            )
        self.connection.commit()

    def new_transaction(self, pool_id: int, transaction: Transaction, token_reversed: bool):
        direction = transaction.direction(token_reversed)
        base_volume = transaction.base_volume(token_reversed)
        quote_volume = transaction.quote_volume(token_reversed)
        price = transaction.price(token_reversed)
        created_at_ms = transaction.created_at // 1000

        self.cursor.execute(
            f'''
                INSERT INTO {self.transactions_table}
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) as alias
                ON DUPLICATE KEY UPDATE
                transaction_type = alias.transaction_type,
                from_account = alias.from_account,
                amount_0_in = alias.amount_0_in,
                amount_0_out = alias.amount_0_out,
                amount_1_in = alias.amount_1_in,
                amount_1_out = alias.amount_1_out,
                liquidity = alias.liquidity,
                price = alias.price,
                volume = alias.volume,
                quote_volume = alias.quote_volume,
                direction = alias.direction,
                token_reversed = alias.token_reversed,
                created_at = alias.created_at
            ''',
            (pool_id,
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

        self.update_candles_for_transaction(
            pool_id=pool_id,
            transaction=transaction,
            token_reversed=token_reversed,
            created_at_ms=created_at_ms,
            price=price,
            base_volume=base_volume,
            quote_volume=quote_volume,
        )

        return {
            'pool_id': pool_id,
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

    def new_transactions(self, pool_id: int, transactions: list[Transaction]):
        _transactions = []

        for transaction in transactions:
            # For each transaction we actually have two direction so we need to create two transactions
            _transactions.append(self.new_transaction(pool_id, transaction, False))
            if transaction.record_reverse():
                _transactions.append(self.new_transaction(pool_id, transaction, True))

        self.connection.commit()

        return _transactions

    def load_candle(self, pool_id: int, token_reversed: bool, interval: str, bucket_start_ms: int):
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
                WHERE pool_id = %s
                AND token_reversed = %s
                AND interval_name = %s
                AND bucket_start_ms = %s
            ''',
            (pool_id, token_reversed, interval, bucket_start_ms),
        )
        row = self.cursor_dict.fetchone()

        if row is None:
            return None
        if row['quote_volume'] is None:
            candle = self.rebuild_candle_from_transactions(
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                bucket_start_ms=bucket_start_ms,
            )
            if candle is None:
                return None

            bucket_key = build_candle_bucket_key(
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
    ):
        bucket_end_ms = bucket_start_ms + get_interval_bucket_ms(interval) - 1
        query = build_kline_points_query(
            table_name=self.transactions_table,
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
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) as alias
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
    ):
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
                WHERE pool_id = %s
                AND token_reversed = %s
                AND interval_name = %s
                AND bucket_start_ms = %s
            ''',
            (pool_id, token_reversed, interval, bucket_start_ms),
        )
        row = self.cursor_dict.fetchone()
        if row is None:
            return None
        if row['quote_volume'] is None:
            return None

        return {
            'timestamp': int(row['bucket_start_ms']),
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'base_volume': float(row['volume']),
            'quote_volume': float(row['quote_volume']),
        }

    def update_candles_for_transaction(
        self,
        pool_id: int,
        transaction: Transaction,
        token_reversed: bool,
        created_at_ms: int,
        price: float,
        base_volume: float,
        quote_volume: float,
    ):
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
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=created_at_ms,
            )
            existing = self.load_candle(
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                bucket_start_ms=bucket_key.bucket_start_ms,
            )
            candle = apply_candle_update(existing=existing, update=update)
            self.save_candle(bucket_key, candle)

    def get_pool_id(self, token_0: str, token_1: str) -> (int, str, str, bool):
        token_1 = token_1 if token_1 is not None else 'TLINERA'
        token_0 = token_0 if token_0 is not None else 'TLINERA'

        self.cursor.execute(
            f'''SELECT pool_id FROM {self.pools_table}
                WHERE token_0 = "{token_0}"
                AND token_1 = "{token_1}"
            '''
        )
        pool_ids = [row[0] for row in self.cursor.fetchall()]
        if len(pool_ids) > 1:
            raise(Exception('Invalid token pair'))

        token_reversed = False

        if len(pool_ids) == 0:
            self.cursor.execute(
                f'''SELECT pool_id FROM {self.pools_table}
                    WHERE token_0 = "{token_1}"
                    AND token_1 = "{token_0}"
                '''
            )
            pool_ids = [row[0] for row in self.cursor.fetchall()]
            token_reversed = True

        if len(pool_ids) != 1:
            raise(Exception('Invalid token pair'))

        return (pool_ids[0], token_0, token_1, token_reversed)

    def get_transactions_information(self, token_0: str, token_1: str):
        if token_0 is None or token_1 is None:
            query = f'''
                SELECT
                    COUNT(*) AS count,
                    MAX(created_at) AS timestamp_begin,
                    MIN(created_at) AS timestamp_end
                FROM {self.transactions_table}
            '''
        else:
            try:
                (pool_id, token_0, token_1, token_reversed) = self.get_pool_id(token_0, token_1)
            except Exception as e:
                print(f'Failed get pool {token_0}:{token_1} -> ERROR {e}')
                return []

            query = f'''
                SELECT
                    COUNT(*) AS count,
                    MAX(created_at) AS timestamp_begin,
                    MIN(created_at) AS timestamp_end
                FROM {self.transactions_table}
                WHERE pool_id = {pool_id}
                AND token_reversed = {token_reversed}
            '''

        self.cursor_dict.execute(query)
        return self.cursor_dict.fetchone()

    def get_transactions(self, token_0: str, token_1: str, start_at: int, end_at: int):
        if token_0 is None or token_1 is None:
            query = f'''
                SELECT * FROM {self.transactions_table}
                WHERE created_at >= {start_at}
                AND created_at <= {end_at}
            '''
        else:
            try:
                (pool_id, token_0, token_1, token_reversed) = self.get_pool_id(token_0, token_1)
            except Exception as e:
                print(f'Failed get pool {token_0}:{token_1} -> ERROR {e}')
                return []

            query = f'''
                SELECT * FROM {self.transactions_table}
                WHERE pool_id = {pool_id}
                AND token_reversed = {token_reversed}
                AND created_at >= {start_at}
                AND created_at <= {end_at}
            '''

        self.cursor_dict.execute(query)
        return self.cursor_dict.fetchall()

    def get_kline_information(self, token_0: str, token_1: str, interval: str):
        (pool_id, token_0, token_1, token_reversed) = self.get_pool_id(token_0, token_1)

        query = f'''
            SELECT
                COUNT(*) AS count,
                MAX(created_at) AS timestamp_begin,
                MIN(created_at) AS timestamp_end
            FROM {self.transactions_table}
            WHERE pool_id = {pool_id}
            AND token_reversed = {token_reversed}
            AND transaction_type != 'AddLiquidity'
            AND transaction_type != 'RemoveLiquidity';
        '''
        self.cursor_dict.execute(query)
        return self.cursor_dict.fetchone()

    def get_kline(self, token_0: str, token_1: str, start_at: int, end_at: int, interval: str):
        request_started_at = time.perf_counter()
        (pool_id, token_0, token_1, token_reversed) = self.get_pool_id(token_0, token_1)
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
            return (token_0, token_1, points)

        self.log_kline_event(
            event='transactions_fallback_start',
            interval=interval,
            pool_id=pool_id,
            token_reversed=token_reversed,
        )
        points = self.get_kline_from_transactions(
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

        return (token_0, token_1, points)

    def get_kline_from_candles(
        self,
        pool_id: int,
        token_reversed: bool,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        interval: str,
    ):
        interval = interval if interval is not None else '1min'
        query_start_at = build_candle_bucket_key(
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=interval,
            created_at_ms=start_at,
        ).bucket_start_ms
        query_end_at = build_candle_bucket_key(
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
                WHERE pool_id = %s
                AND token_reversed = %s
                AND interval_name = %s
                AND bucket_start_ms >= %s
                AND bucket_start_ms <= %s
                ORDER BY bucket_start_ms ASC
            ''',
            (pool_id, token_reversed, interval, query_start_at, query_end_at),
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
            return []

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

        return filter_zero_volume_candles(json_data)

    def get_kline_from_transactions(
        self,
        pool_id: int,
        token_reversed: bool,
        start_at: int,
        end_at: int,
        interval: str,
    ):
        query = build_kline_points_query(
            table_name=self.transactions_table,
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
        return filter_zero_volume_candles(candle_items)

    def get_last_kline(self, token_0: str, token_1: str, interval: str):
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

        (token_0, token_1, points) = self.get_kline(token_0, token_1, start_at, end_at, interval)

        return  (token_0, token_1, start_at, end_at, interval, points)

    def get_ticker(self, interval: str):
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
                JOIN pools p ON t.pool_id = p.pool_id
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
                JOIN pools p ON t.pool_id = p.pool_id
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
                    JOIN pools p ON t.pool_id = p.pool_id
                    WHERE
                        p.token_1 = 'TLINERA'
                        AND t.token_reversed = {token_reversed}
                    UNION ALL
                    SELECT
                        p.token_1 AS token,
                        t.created_at,
                        1 / t.price AS price
                    FROM transactions t
                    JOIN pools p ON t.pool_id = p.pool_id
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
                    WHERE t2.pool_id = p.pool_id
                      AND t2.created_at >= {start_at}
                      AND t2.created_at <= {end_at}
                      AND t2.transaction_type IN ('BuyToken0', 'SellToken0')
                    ORDER BY t2.created_at DESC
                    LIMIT 1
                ) AS price_now,
                (
                    SELECT t3.price
                    FROM transactions t3
                    WHERE t3.pool_id = p.pool_id
                      AND t3.created_at >= {start_at}
                      AND t3.created_at <= {end_at}
                      AND t3.transaction_type IN ('BuyToken0', 'SellToken0')
                    ORDER BY t3.created_at ASC
                    LIMIT 1
                ) AS price_start
            FROM transactions t
            JOIN pools p
              ON t.pool_id = p.pool_id
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
        self.cursor_dict.execute(query)
        return self.cursor_dict.fetchall()

    def get_protocol_stats(self, pools: list[Pool]):
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
                WHERE
                    t.created_at >= {start_at}
                    AND t.token_reversed = {token_reversed}
            ),
            previous AS (
                SELECT
                    SUM(COALESCE(t.amount_1_in, 0) + COALESCE(t.amount_1_out, 0)) AS volume
                FROM transactions t
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
                JOIN pools p ON t.pool_id = p.pool_id
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
                JOIN pools p ON t.pool_id = p.pool_id
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
                JOIN pools p ON t.pool_id = p.pool_id
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
                JOIN pools p ON t.pool_id = p.pool_id
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
