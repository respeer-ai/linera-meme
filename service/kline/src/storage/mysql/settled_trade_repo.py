from storage.mysql.canonical_fingerprint import CanonicalFingerprint
from storage.mysql.repository_connection_mixin import MysqlRepositoryConnectionMixin


class SettledTradeRepository(MysqlRepositoryConnectionMixin):
    POOL_TIME_INDEX = 'idx_settled_trades_pool_time'

    def __init__(self, connection):
        self.connection = connection
        self.fingerprint = CanonicalFingerprint()
        self.settled_trades_table = 'settled_trades'

    def _column_exists(self, cursor, column_name: str) -> bool:
        cursor.execute(
            f'''
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
            ''',
            (self.settled_trades_table, column_name),
        )
        return cursor.fetchone() is not None

    def ensure_schema(self) -> None:
        cursor = self.cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.settled_trades_table} (
                    settled_trade_id VARCHAR(255) NOT NULL,
                    normalized_event_id VARCHAR(255) NOT NULL,
                    pool_application_id VARCHAR(256) NOT NULL,
                    pool_chain_id VARCHAR(64) NULL,
                    from_account VARCHAR(255) NULL,
                    block_hash VARCHAR(64) NULL,
                    trade_time_ms BIGINT NULL,
                    transaction_index INT NULL,
                    transaction_id BIGINT NULL,
                    side VARCHAR(32) NOT NULL,
                    amount_0_in VARCHAR(64) NULL,
                    amount_0_out VARCHAR(64) NULL,
                    amount_1_in VARCHAR(64) NULL,
                    amount_1_out VARCHAR(64) NULL,
                    amount_in VARCHAR(64) NOT NULL,
                    amount_out VARCHAR(64) NOT NULL,
                    price_numerator VARCHAR(64) NOT NULL,
                    price_denominator VARCHAR(64) NOT NULL,
                    source_event_key VARCHAR(255) NOT NULL,
                    event_payload_json LONGTEXT NOT NULL,
                    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    PRIMARY KEY (settled_trade_id),
                    UNIQUE KEY uq_settled_trade_event (normalized_event_id),
                    KEY idx_settled_trades_pool_time (pool_application_id, trade_time_ms, transaction_index),
                    KEY idx_settled_trades_source_event (source_event_key)
                )
                '''
            )
            cursor.execute(
                f'''
                ALTER TABLE {self.settled_trades_table}
                MODIFY COLUMN pool_application_id VARCHAR(256) NOT NULL
                '''
            )
            cursor.execute(
                f'''
                UPDATE {self.settled_trades_table}
                SET pool_application_id = CONCAT('0x', pool_application_id, '@', pool_chain_id)
                WHERE pool_chain_id IS NOT NULL
                  AND pool_chain_id != ''
                  AND pool_application_id NOT LIKE '%@%'
                  AND pool_application_id NOT LIKE '0x%'
                  AND CHAR_LENGTH(pool_application_id) IN (40, 64)
                  AND pool_application_id REGEXP '^[0-9A-Fa-f]+$'
                '''
            )
            from_account_exists = self._column_exists(cursor, 'from_account')
            if not from_account_exists:
                cursor.execute(
                    f'''
                    ALTER TABLE {self.settled_trades_table}
                    ADD COLUMN from_account VARCHAR(255) NULL
                    AFTER pool_chain_id
                    '''
                )
            amount_0_in_exists = self._column_exists(cursor, 'amount_0_in')
            if not amount_0_in_exists:
                cursor.execute(
                    f'''
                    ALTER TABLE {self.settled_trades_table}
                    ADD COLUMN amount_0_in VARCHAR(64) NULL
                    AFTER side
                    '''
                )
            amount_0_out_exists = self._column_exists(cursor, 'amount_0_out')
            if not amount_0_out_exists:
                cursor.execute(
                    f'''
                    ALTER TABLE {self.settled_trades_table}
                    ADD COLUMN amount_0_out VARCHAR(64) NULL
                    AFTER amount_0_in
                    '''
                )
            amount_1_in_exists = self._column_exists(cursor, 'amount_1_in')
            if not amount_1_in_exists:
                cursor.execute(
                    f'''
                    ALTER TABLE {self.settled_trades_table}
                    ADD COLUMN amount_1_in VARCHAR(64) NULL
                    AFTER amount_0_out
                    '''
                )
            amount_1_out_exists = self._column_exists(cursor, 'amount_1_out')
            if not amount_1_out_exists:
                cursor.execute(
                    f'''
                    ALTER TABLE {self.settled_trades_table}
                    ADD COLUMN amount_1_out VARCHAR(64) NULL
                    AFTER amount_1_in
                    '''
                )
            self._ensure_index(
                cursor,
                self.POOL_TIME_INDEX,
                ('pool_application_id', 'trade_time_ms', 'transaction_id', 'settled_trade_id'),
            )
            self.connection.commit()
        finally:
            cursor.close()

    def _ensure_index(self, cursor, index_name: str, expected_columns: tuple[str, ...]) -> None:
        cursor.execute(f'SHOW INDEX FROM {self.settled_trades_table}')
        matching_rows = [
            row for row in cursor.fetchall()
            if len(row) > 4 and row[2] == index_name
        ]
        existing_columns = tuple(
            row[4] for row in sorted(matching_rows, key=lambda row: row[3])
        )
        if existing_columns == expected_columns:
            return
        if existing_columns:
            cursor.execute(f'DROP INDEX {index_name} ON {self.settled_trades_table}')
        cursor.execute(
            f'CREATE INDEX {index_name} ON {self.settled_trades_table} ({", ".join(expected_columns)})'
        )

    def upsert_settled_trades(self, trades: list[dict[str, object]]) -> int:
        if not trades:
            return 0
        cursor = self.cursor()
        try:
            for trade in trades:
                cursor.execute(
                    f'''
                    INSERT INTO {self.settled_trades_table} (
                        settled_trade_id,
                        normalized_event_id,
                        pool_application_id,
                        pool_chain_id,
                        from_account,
                        block_hash,
                        trade_time_ms,
                        transaction_index,
                        transaction_id,
                        side,
                        amount_0_in,
                        amount_0_out,
                        amount_1_in,
                        amount_1_out,
                        amount_in,
                        amount_out,
                        price_numerator,
                        price_denominator,
                        source_event_key,
                        event_payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pool_application_id = VALUES(pool_application_id),
                        pool_chain_id = VALUES(pool_chain_id),
                        from_account = VALUES(from_account),
                        block_hash = VALUES(block_hash),
                        trade_time_ms = VALUES(trade_time_ms),
                        transaction_index = VALUES(transaction_index),
                        transaction_id = VALUES(transaction_id),
                        side = VALUES(side),
                        amount_0_in = VALUES(amount_0_in),
                        amount_0_out = VALUES(amount_0_out),
                        amount_1_in = VALUES(amount_1_in),
                        amount_1_out = VALUES(amount_1_out),
                        amount_in = VALUES(amount_in),
                        amount_out = VALUES(amount_out),
                        price_numerator = VALUES(price_numerator),
                        price_denominator = VALUES(price_denominator),
                        source_event_key = VALUES(source_event_key),
                        event_payload_json = VALUES(event_payload_json)
                    ''',
                    (
                        trade['settled_trade_id'],
                        trade['normalized_event_id'],
                        trade['pool_application_id'],
                        trade.get('pool_chain_id'),
                        trade.get('from_account'),
                        trade.get('block_hash'),
                        trade.get('trade_time_ms'),
                        trade.get('transaction_index'),
                        trade.get('transaction_id'),
                        trade['side'],
                        trade.get('amount_0_in'),
                        trade.get('amount_0_out'),
                        trade.get('amount_1_in'),
                        trade.get('amount_1_out'),
                        trade['amount_in'],
                        trade['amount_out'],
                        trade['price_numerator'],
                        trade['price_denominator'],
                        trade['source_event_key'],
                        self.fingerprint.build_json(trade.get('event_payload_json') or {}),
                    ),
                )
            self.connection.commit()
            return len(trades)
        finally:
            cursor.close()
