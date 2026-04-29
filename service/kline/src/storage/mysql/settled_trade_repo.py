from storage.mysql.canonical_fingerprint import CanonicalFingerprint


class SettledTradeRepository:
    def __init__(self, connection):
        self.connection = connection
        self.fingerprint = CanonicalFingerprint()
        self.settled_trades_table = 'settled_trades'

    def ensure_schema(self) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.settled_trades_table} (
                    settled_trade_id VARCHAR(255) NOT NULL,
                    normalized_event_id VARCHAR(255) NOT NULL,
                    pool_application_id VARCHAR(128) NOT NULL,
                    pool_chain_id VARCHAR(64) NULL,
                    block_hash VARCHAR(64) NULL,
                    trade_time_ms BIGINT NULL,
                    transaction_index INT NULL,
                    transaction_id BIGINT NULL,
                    side VARCHAR(32) NOT NULL,
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
            self.connection.commit()
        finally:
            cursor.close()

    def upsert_settled_trades(self, trades: list[dict[str, object]]) -> int:
        if not trades:
            return 0
        cursor = self.connection.cursor()
        try:
            for trade in trades:
                cursor.execute(
                    f'''
                    INSERT INTO {self.settled_trades_table} (
                        settled_trade_id,
                        normalized_event_id,
                        pool_application_id,
                        pool_chain_id,
                        block_hash,
                        trade_time_ms,
                        transaction_index,
                        transaction_id,
                        side,
                        amount_in,
                        amount_out,
                        price_numerator,
                        price_denominator,
                        source_event_key,
                        event_payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pool_application_id = VALUES(pool_application_id),
                        pool_chain_id = VALUES(pool_chain_id),
                        block_hash = VALUES(block_hash),
                        trade_time_ms = VALUES(trade_time_ms),
                        transaction_index = VALUES(transaction_index),
                        transaction_id = VALUES(transaction_id),
                        side = VALUES(side),
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
                        trade.get('block_hash'),
                        trade.get('trade_time_ms'),
                        trade.get('transaction_index'),
                        trade.get('transaction_id'),
                        trade['side'],
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
