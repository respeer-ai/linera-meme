import mysql.connector
from swap import Transaction, Pool
from datetime import datetime
import pandas as pd
import time
import warnings
import numpy as np


class Db:
    def __init__(self, host, db_name, username, password, clean_kline):
        self.host = host
        self.db_name = db_name
        self.username = username
        self.password = password
        self.config = {
            'user': self.username,
            'password': self.password,
            'host': self.host,
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
                    created_at DATETIME,
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
             datetime.fromtimestamp(transaction.created_at / 1000000).strftime('%Y-%m-%d %H:%M:%S'))
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
            'created_at': datetime.fromtimestamp(transaction.created_at / 1000000).strftime('%Y-%m-%d %H:%M:%S')
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

    def get_transactions(self, token_0: str, token_1: str, start_at: int, end_at: int):
        try:
            (pool_id, token_0, token_1, token_reversed) = self.get_pool_id(token_0, token_1)
        except Exception as e:
            return []

        start_at = datetime.fromtimestamp(start_at).strftime('%Y-%m-%d %H:%M:%S')
        end_at = datetime.fromtimestamp(end_at).strftime('%Y-%m-%d %H:%M:%S')

        query = f'''
            SELECT * FROM {self.transactions_table}
            WHERE pool_id = {pool_id}
            AND created_at BETWEEN '{start_at}' AND '{end_at}'
            AND token_reversed = {token_reversed}
        '''
        self.cursor_dict.execute(query)
        return self.cursor_dict.fetchall()

    def get_kline(self, token_0: str, token_1: str, start_at: int, end_at: int, interval: str):
        (pool_id, token_0, token_1, token_reversed) = self.get_pool_id(token_0, token_1)

        start_at = datetime.fromtimestamp(start_at).strftime('%Y-%m-%d %H:%M:%S')
        end_at = datetime.fromtimestamp(end_at).strftime('%Y-%m-%d %H:%M:%S')

        query = f'''
            SELECT created_at, price, volume FROM {self.transactions_table}
            WHERE pool_id = {pool_id}
            AND created_at BETWEEN '{start_at}' AND '{end_at}'
            AND token_reversed = {token_reversed}
            AND transaction_type != 'AddLiquidity'
            AND transaction_type != 'RemoveLiquidity'
        '''
        df = pd.read_sql(query, self.connection)
        df['created_at'] = pd.to_datetime(df['created_at'])
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
        df_interval = df_interval.loc[~(df_interval[['open', 'high', 'low', 'close', 'volume']] == 0).all(axis=1)]

        json_data = []
        for index, row in df_interval.iterrows():
            json_data.append({
                'timestamp': index.strftime('%Y-%m-%dT%H:%M:%S'),
                'open': row['open'],
                'high': row['high'],
                'low': row['low'],
                'close': row['close'],
                'volume': row['volume'],
            })

        return (token_0, token_1, json_data)

    def get_last_kline(self, token_0: str, token_1: str, interval: str):
        end_at = time.time()
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

        (token_0, token_1, points) = self.get_kline(token_0, token_1, start_at, end_at, interval)

        return  (token_0, token_1, start_at, end_at, interval, points)

    def close(self):
        self.cursor.close()
        self.cursor_dict.close()
        self.connection.close()

