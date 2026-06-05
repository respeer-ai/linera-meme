from storage.mysql.canonical_fingerprint import CanonicalFingerprint


from storage.mysql.repository_connection_mixin import MysqlRepositoryConnectionMixin


class SettledLiquidityChangeRepository(MysqlRepositoryConnectionMixin):
    def __init__(self, connection):
        self.connection = connection
        self.fingerprint = CanonicalFingerprint()
        self.settled_liquidity_changes_table = 'settled_liquidity_changes'

    def _column_exists(self, cursor, column_name: str) -> bool:
        cursor.execute(
            f'''
            SELECT COLUMN_NAME FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
            ''',
            (self.settled_liquidity_changes_table, column_name),
        )
        return cursor.fetchone() is not None

    def ensure_schema(self) -> None:
        cursor = self.cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.settled_liquidity_changes_table} (
                    settled_liquidity_change_id VARCHAR(255) NOT NULL,
                    normalized_event_id VARCHAR(255) NOT NULL,
                    pool_application_id VARCHAR(256) NOT NULL,
                    pool_chain_id VARCHAR(64) NULL,
                    owner VARCHAR(255) NOT NULL,
                    block_hash VARCHAR(64) NULL,
                    event_time_ms BIGINT NULL,
                    transaction_index INT NULL,
                    transaction_id BIGINT NULL,
                    change_type VARCHAR(32) NOT NULL,
                    liquidity_delta VARCHAR(64) NOT NULL,
                    is_position_liquidity BOOLEAN NOT NULL DEFAULT TRUE,
                    liquidity_semantics VARCHAR(64) NOT NULL DEFAULT 'position_liquidity',
                    amount_0_delta VARCHAR(64) NOT NULL,
                    amount_1_delta VARCHAR(64) NOT NULL,
                    source_event_key VARCHAR(255) NOT NULL,
                    event_payload_json LONGTEXT NOT NULL,
                    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    PRIMARY KEY (settled_liquidity_change_id),
                    UNIQUE KEY uq_settled_liquidity_event (normalized_event_id),
                    KEY idx_settled_liquidity_owner (owner, pool_application_id, event_time_ms),
                    KEY idx_settled_liquidity_source_event (source_event_key)
                )
                '''
            )
            cursor.execute(
                f'''
                ALTER TABLE {self.settled_liquidity_changes_table}
                MODIFY COLUMN pool_application_id VARCHAR(256) NOT NULL
                '''
            )
            cursor.execute(
                f'''
                UPDATE {self.settled_liquidity_changes_table}
                SET pool_application_id = CONCAT('0x', pool_application_id, '@', pool_chain_id)
                WHERE pool_chain_id IS NOT NULL
                  AND pool_chain_id != ''
                  AND pool_application_id NOT LIKE '%@%'
                  AND pool_application_id NOT LIKE '0x%'
                  AND CHAR_LENGTH(pool_application_id) IN (40, 64)
                  AND pool_application_id REGEXP '^[0-9A-Fa-f]+$'
                '''
            )
            if not self._column_exists(cursor, 'is_position_liquidity'):
                cursor.execute(
                    f'''
                    ALTER TABLE {self.settled_liquidity_changes_table}
                    ADD COLUMN is_position_liquidity BOOLEAN NOT NULL DEFAULT TRUE
                    AFTER liquidity_delta
                    '''
                )
            if not self._column_exists(cursor, 'liquidity_semantics'):
                cursor.execute(
                    f'''
                    ALTER TABLE {self.settled_liquidity_changes_table}
                    ADD COLUMN liquidity_semantics VARCHAR(64) NOT NULL DEFAULT 'position_liquidity'
                    AFTER is_position_liquidity
                    '''
                )
            cursor.execute(
                f'''
                UPDATE {self.settled_liquidity_changes_table}
                SET
                    is_position_liquidity = TRUE,
                    liquidity_semantics = 'position_liquidity'
                WHERE liquidity_semantics IS NULL
                   OR liquidity_semantics = ''
                '''
            )
            self.connection.commit()
        finally:
            cursor.close()

    def upsert_settled_liquidity_changes(self, changes: list[dict[str, object]]) -> int:
        if not changes:
            return 0
        cursor = self.cursor()
        try:
            for change in changes:
                cursor.execute(
                    f'''
                    INSERT INTO {self.settled_liquidity_changes_table} (
                        settled_liquidity_change_id,
                        normalized_event_id,
                        pool_application_id,
                        pool_chain_id,
                        owner,
                        block_hash,
                        event_time_ms,
                        transaction_index,
                        transaction_id,
                        change_type,
                        liquidity_delta,
                        is_position_liquidity,
                        liquidity_semantics,
                        amount_0_delta,
                        amount_1_delta,
                        source_event_key,
                        event_payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pool_application_id = VALUES(pool_application_id),
                        pool_chain_id = VALUES(pool_chain_id),
                        owner = VALUES(owner),
                        block_hash = VALUES(block_hash),
                        event_time_ms = VALUES(event_time_ms),
                        transaction_index = VALUES(transaction_index),
                        transaction_id = VALUES(transaction_id),
                        change_type = VALUES(change_type),
                        liquidity_delta = VALUES(liquidity_delta),
                        is_position_liquidity = VALUES(is_position_liquidity),
                        liquidity_semantics = VALUES(liquidity_semantics),
                        amount_0_delta = VALUES(amount_0_delta),
                        amount_1_delta = VALUES(amount_1_delta),
                        source_event_key = VALUES(source_event_key),
                        event_payload_json = VALUES(event_payload_json)
                    ''',
                    (
                        change['settled_liquidity_change_id'],
                        change['normalized_event_id'],
                        change['pool_application_id'],
                        change.get('pool_chain_id'),
                        change['owner'],
                        change.get('block_hash'),
                        change.get('event_time_ms'),
                        change.get('transaction_index'),
                        change.get('transaction_id'),
                        change['change_type'],
                        change['liquidity_delta'],
                        bool(change.get('is_position_liquidity', True)),
                        change.get('liquidity_semantics') or 'position_liquidity',
                        change['amount_0_delta'],
                        change['amount_1_delta'],
                        change['source_event_key'],
                        self.fingerprint.build_json(change.get('event_payload_json') or {}),
                    ),
                )
            self.connection.commit()
            return len(changes)
        finally:
            cursor.close()
