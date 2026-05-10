from storage.mysql.canonical_fingerprint import CanonicalFingerprint


class PoolStateSnapshotRepository:
    def __init__(self, connection):
        self.connection = connection
        self.fingerprint = CanonicalFingerprint()
        self.pool_state_table = 'pool_state_v2'

    def ensure_schema(self) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.pool_state_table} (
                    pool_state_id VARCHAR(255) NOT NULL,
                    pool_application_id VARCHAR(256) NOT NULL,
                    pool_chain_id VARCHAR(64) NULL,
                    last_trade_time_ms BIGINT NULL,
                    last_liquidity_event_time_ms BIGINT NULL,
                    last_transaction_id BIGINT NULL,
                    swap_count BIGINT NOT NULL DEFAULT 0,
                    live_reserve_0 VARCHAR(64) NOT NULL,
                    live_reserve_1 VARCHAR(64) NOT NULL,
                    live_total_supply VARCHAR(64) NOT NULL,
                    live_k_last VARCHAR(64) NOT NULL,
                    fee_free_basis_transaction_id BIGINT NULL,
                    fee_free_basis_time_ms BIGINT NULL,
                    fee_free_reserve_0 VARCHAR(64) NOT NULL,
                    fee_free_reserve_1 VARCHAR(64) NOT NULL,
                    fee_free_total_supply VARCHAR(64) NOT NULL,
                    source_event_key VARCHAR(255) NOT NULL,
                    state_payload_json LONGTEXT NOT NULL,
                    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    PRIMARY KEY (pool_state_id),
                    UNIQUE KEY uq_pool_state_pool_application (pool_application_id),
                    KEY idx_pool_state_trade_time (last_trade_time_ms),
                    KEY idx_pool_state_swap_count (swap_count)
                )
                '''
            )
            self._migrate_pool_application_id_width(cursor)
            self._migrate_legacy_pool_application_accounts(cursor)
            self.connection.commit()
        finally:
            cursor.close()

    def _migrate_pool_application_id_width(self, cursor) -> None:
        cursor.execute(
            f'''
            ALTER TABLE {self.pool_state_table}
            MODIFY COLUMN pool_application_id VARCHAR(256) NOT NULL
            '''
        )

    def _migrate_legacy_pool_application_accounts(self, cursor) -> None:
        cursor.execute(
            f'''
            UPDATE {self.pool_state_table}
            SET
                pool_state_id = CONCAT(SUBSTRING_INDEX(pool_application_id, ':', -1), '@', pool_chain_id),
                pool_application_id = CONCAT(SUBSTRING_INDEX(pool_application_id, ':', -1), '@', pool_chain_id)
            WHERE pool_chain_id IS NOT NULL
              AND pool_chain_id != ''
              AND pool_application_id LIKE '%:%'
              AND SUBSTRING_INDEX(pool_application_id, ':', 1) = pool_chain_id
              AND SUBSTRING_INDEX(pool_application_id, ':', -1) REGEXP '^0x[0-9A-Fa-f]{{40}}$|^0x[0-9A-Fa-f]{{64}}$'
              AND NOT EXISTS (
                  SELECT 1
                  FROM (
                      SELECT pool_application_id AS existing_pool_application_id
                      FROM {self.pool_state_table}
                  ) existing_pool_state
                  WHERE existing_pool_state.existing_pool_application_id = CONCAT(
                      SUBSTRING_INDEX({self.pool_state_table}.pool_application_id, ':', -1),
                      '@',
                      {self.pool_state_table}.pool_chain_id
                  )
              )
            '''
        )

    def upsert_pool_states(self, states: list[dict[str, object]]) -> int:
        if not states:
            return 0
        cursor = self.connection.cursor()
        try:
            for state in states:
                cursor.execute(
                    f'''
                    INSERT INTO {self.pool_state_table} (
                        pool_state_id,
                        pool_application_id,
                        pool_chain_id,
                        last_trade_time_ms,
                        last_liquidity_event_time_ms,
                        last_transaction_id,
                        swap_count,
                        live_reserve_0,
                        live_reserve_1,
                        live_total_supply,
                        live_k_last,
                        fee_free_basis_transaction_id,
                        fee_free_basis_time_ms,
                        fee_free_reserve_0,
                        fee_free_reserve_1,
                        fee_free_total_supply,
                        source_event_key,
                        state_payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pool_application_id = VALUES(pool_application_id),
                        pool_chain_id = VALUES(pool_chain_id),
                        last_trade_time_ms = VALUES(last_trade_time_ms),
                        last_liquidity_event_time_ms = VALUES(last_liquidity_event_time_ms),
                        last_transaction_id = VALUES(last_transaction_id),
                        swap_count = VALUES(swap_count),
                        live_reserve_0 = VALUES(live_reserve_0),
                        live_reserve_1 = VALUES(live_reserve_1),
                        live_total_supply = VALUES(live_total_supply),
                        live_k_last = VALUES(live_k_last),
                        fee_free_basis_transaction_id = VALUES(fee_free_basis_transaction_id),
                        fee_free_basis_time_ms = VALUES(fee_free_basis_time_ms),
                        fee_free_reserve_0 = VALUES(fee_free_reserve_0),
                        fee_free_reserve_1 = VALUES(fee_free_reserve_1),
                        fee_free_total_supply = VALUES(fee_free_total_supply),
                        source_event_key = VALUES(source_event_key),
                        state_payload_json = VALUES(state_payload_json)
                    ''',
                    (
                        state['pool_state_id'],
                        state['pool_application_id'],
                        state.get('pool_chain_id'),
                        state.get('last_trade_time_ms'),
                        state.get('last_liquidity_event_time_ms'),
                        state.get('last_transaction_id'),
                        state.get('swap_count', 0),
                        state['live_reserve_0'],
                        state['live_reserve_1'],
                        state['live_total_supply'],
                        state['live_k_last'],
                        state.get('fee_free_basis_transaction_id'),
                        state.get('fee_free_basis_time_ms'),
                        state['fee_free_reserve_0'],
                        state['fee_free_reserve_1'],
                        state['fee_free_total_supply'],
                        state['source_event_key'],
                        self.fingerprint.build_json(state.get('state_payload_json') or {}),
                    ),
                )
            self.connection.commit()
            return len(states)
        finally:
            cursor.close()

    def get_pool_state(
        self,
        *,
        pool_application_id: str,
    ) -> dict | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT *
                FROM {self.pool_state_table}
                WHERE pool_application_id = %s
                LIMIT 1
                ''',
                (pool_application_id,),
            )
            return cursor.fetchone()
        finally:
            cursor.close()
