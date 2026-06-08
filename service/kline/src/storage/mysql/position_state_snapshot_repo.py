from storage.mysql.canonical_fingerprint import CanonicalFingerprint


class PositionStateSnapshotRepository:
    def __init__(self, connection):
        self.connection = connection
        self.fingerprint = CanonicalFingerprint()
        self.position_state_table = 'position_state_v2'

    def ensure_schema(self) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.position_state_table} (
                    position_state_id VARCHAR(512) NOT NULL,
                    owner VARCHAR(255) NOT NULL,
                    pool_application_id VARCHAR(256) NOT NULL,
                    pool_chain_id VARCHAR(64) NULL,
                    status VARCHAR(32) NOT NULL,
                    basis_type VARCHAR(32) NOT NULL,
                    current_liquidity VARCHAR(64) NOT NULL,
                    basis_liquidity VARCHAR(64) NOT NULL,
                    basis_amount_0 VARCHAR(64) NOT NULL,
                    basis_amount_1 VARCHAR(64) NOT NULL,
                    basis_time_ms BIGINT NULL,
                    basis_transaction_id BIGINT NULL,
                    source_event_key VARCHAR(512) NOT NULL,
                    state_payload_json LONGTEXT NOT NULL,
                    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    PRIMARY KEY (position_state_id),
                    UNIQUE KEY uq_position_state_owner_pool_status (owner, pool_application_id, status),
                    KEY idx_position_state_owner_status (owner, status, updated_at),
                    KEY idx_position_state_pool_basis_time (pool_application_id, basis_time_ms)
                )
                '''
            )
            self._migrate_pool_application_id_width(cursor)
            self.connection.commit()
        finally:
            cursor.close()

    def _migrate_pool_application_id_width(self, cursor) -> None:
        cursor.execute(
            f'''
            ALTER TABLE {self.position_state_table}
            MODIFY COLUMN position_state_id VARCHAR(512) NOT NULL,
            MODIFY COLUMN pool_application_id VARCHAR(256) NOT NULL,
            MODIFY COLUMN source_event_key VARCHAR(512) NOT NULL
            '''
        )

    def upsert_position_states(self, states: list[dict[str, object]]) -> int:
        if not states:
            return 0
        cursor = self.connection.cursor()
        try:
            for state in states:
                self._execute_upsert(cursor, state)
            self.connection.commit()
            return len(states)
        finally:
            cursor.close()

    def replace_position_states(
        self,
        *,
        owner: str,
        pool_application_id: str,
        states: list[dict[str, object]],
    ) -> int:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                DELETE FROM {self.position_state_table}
                WHERE owner = %s
                  AND pool_application_id = %s
                ''',
                (owner, pool_application_id),
            )
            for state in states:
                self._execute_upsert(cursor, state)
            self.connection.commit()
            return len(states)
        finally:
            cursor.close()

    def get_position_state(
        self,
        *,
        owner: str,
        pool_application_id: str,
        status: str = 'active',
    ) -> dict | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT *
                FROM {self.position_state_table}
                WHERE owner = %s
                  AND pool_application_id = %s
                  AND status = %s
                LIMIT 1
                ''',
                (owner, pool_application_id, status),
            )
            return cursor.fetchone()
        finally:
            cursor.close()

    def _execute_upsert(self, cursor, state: dict[str, object]) -> None:
        cursor.execute(
            f'''
            INSERT INTO {self.position_state_table} (
                position_state_id,
                owner,
                pool_application_id,
                pool_chain_id,
                status,
                basis_type,
                current_liquidity,
                basis_liquidity,
                basis_amount_0,
                basis_amount_1,
                basis_time_ms,
                basis_transaction_id,
                source_event_key,
                state_payload_json
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                owner = VALUES(owner),
                pool_application_id = VALUES(pool_application_id),
                pool_chain_id = VALUES(pool_chain_id),
                status = VALUES(status),
                basis_type = VALUES(basis_type),
                current_liquidity = VALUES(current_liquidity),
                basis_liquidity = VALUES(basis_liquidity),
                basis_amount_0 = VALUES(basis_amount_0),
                basis_amount_1 = VALUES(basis_amount_1),
                basis_time_ms = VALUES(basis_time_ms),
                basis_transaction_id = VALUES(basis_transaction_id),
                source_event_key = VALUES(source_event_key),
                state_payload_json = VALUES(state_payload_json)
            ''',
            (
                state['position_state_id'],
                state['owner'],
                state['pool_application_id'],
                state.get('pool_chain_id'),
                state['status'],
                state['basis_type'],
                state['current_liquidity'],
                state['basis_liquidity'],
                state['basis_amount_0'],
                state['basis_amount_1'],
                state.get('basis_time_ms'),
                state.get('basis_transaction_id'),
                state['source_event_key'],
                self.fingerprint.build_json(state.get('state_payload_json') or {}),
            ),
        )
