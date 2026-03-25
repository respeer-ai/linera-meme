import mysql.connector
from swap import Transaction, Pool
from datetime import datetime
import pandas as pd
import time
import warnings
import numpy as np


class Db:
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
                    direction VARCHAR(8),
                    token_reversed TINYINT,
                    created_at BIGINT UNSIGNED,
                    PRIMARY KEY (pool_id, transaction_id, token_reversed)
                )
            ''')
            self.connection.commit()

        self.cursor_dict = self.connection.cursor(dictionary=True)


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
        volume = transaction.volume(token_reversed)
        price = transaction.price(token_reversed)

        self.cursor.execute(
            f'''
                INSERT INTO {self.transactions_table}
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) as alias
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
             volume,
             direction,
             token_reversed,
             transaction.created_at // 1000)
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
            'volume': volume,
            'direction': direction,
            'token_reversed': token_reversed,
            'created_at': transaction.created_at // 1000,
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
                WHERE created_at BETWEEN {start_at} AND {end_at}
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
                AND created_at BETWEEN {start_at} AND {end_at}
                AND token_reversed = {token_reversed}
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
        (pool_id, token_0, token_1, token_reversed) = self.get_pool_id(token_0, token_1)

        query = f'''
            SELECT created_at, price, volume FROM {self.transactions_table}
            WHERE pool_id = {pool_id}
            AND created_at BETWEEN {start_at} AND {end_at}
            AND token_reversed = {token_reversed}
            AND transaction_type != 'AddLiquidity'
            AND transaction_type != 'RemoveLiquidity'
        '''
        df = pd.read_sql(query, self.connection)
        df['created_at'] = pd.to_datetime(df['created_at'], unit='ms')
        df.set_index('created_at', inplace=True)
        df.sort_index(inplace=True)

        # 1 minute in default
        interval = interval if interval is not None else '1T'
        df_interval = df.resample(interval).agg({
            'price': ['first', 'max', 'min', 'last'],
            'volume': 'sum'
        })
        df_interval.columns = ['open', 'high', 'low', 'close', 'volume']
        df_interval = df_interval.map(lambda x: np.nan_to_num(x, nan=0.0, posinf=1e308, neginf=01e308))

        # 处理 OHLC 与 volume
        last_close = None
        for idx, row in df_interval.iterrows():
            if row['volume'] == 0 and last_close is not None:
                if last_close is not None:
                    df_interval.at[idx, 'open'] = last_close
                    df_interval.at[idx, 'high'] = last_close
                    df_interval.at[idx, 'low'] = last_close
                    df_interval.at[idx, 'close'] = last_close
            else:
                last_close = row['close']

        json_data = []
        for index, row in df_interval.iterrows():
            json_data.append({
                'timestamp': int(index.timestamp() * 1000),
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
            })

        return (token_0, token_1, json_data)

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
                    -- token / TLINERA
                    SELECT
                        p.token_0 AS token,
                        t.created_at,
                        t.price AS price
                    FROM transactions t
                    JOIN pools p ON t.pool_id = p.pool_id
                    WHERE p.token_1 = 'TLINERA'
                    UNION ALL
                    SELECT
                        p.token_1 AS token,
                        t.created_at,
                        1 / t.price AS price
                    FROM transactions t
                    JOIN pools p ON t.pool_id = p.pool_id
                    WHERE p.token_0 = 'TLINERA'
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

