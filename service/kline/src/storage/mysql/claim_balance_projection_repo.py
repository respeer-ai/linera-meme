import json

from storage.mysql.canonical_fingerprint import CanonicalFingerprint
from storage.mysql.repository_connection_mixin import MysqlRepositoryConnectionMixin


class ClaimBalanceProjectionRepository(MysqlRepositoryConnectionMixin):
    DISPLAY_AMOUNT_SCALE = '1000000000000000000'

    def __init__(self, connection):
        self.connection = connection
        self.fingerprint = CanonicalFingerprint()
        self.claim_balance_deltas_table = 'claim_balance_deltas'
        self.claim_balance_diagnostics_table = 'claim_balance_diagnostics'

    def ensure_schema(self) -> None:
        cursor = self.cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.claim_balance_deltas_table} (
                    claim_balance_delta_id VARCHAR(512) NOT NULL,
                    normalized_event_id VARCHAR(255) NOT NULL,
                    pool_application_id VARCHAR(256) NOT NULL,
                    execution_chain_id VARCHAR(64) NOT NULL,
                    token VARCHAR(256) NOT NULL,
                    owner VARCHAR(255) NOT NULL,
                    balance_kind VARCHAR(32) NOT NULL,
                    delta_amount VARCHAR(64) NOT NULL,
                    delta_direction VARCHAR(16) NOT NULL,
                    block_hash VARCHAR(64) NULL,
                    block_height BIGINT NULL,
                    transaction_index INT NULL,
                    message_index INT NULL,
                    rejected BOOLEAN NOT NULL DEFAULT FALSE,
                    derivation_source VARCHAR(64) NOT NULL,
                    derivation_confidence VARCHAR(32) NOT NULL,
                    source_event_key VARCHAR(255) NOT NULL,
                    event_payload_json LONGTEXT NOT NULL,
                    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    PRIMARY KEY (claim_balance_delta_id),
                    KEY idx_claim_balance_delta_owner (owner(128), pool_application_id(128), execution_chain_id, token(128)),
                    KEY idx_claim_balance_delta_source_event (source_event_key),
                    KEY idx_claim_balance_delta_confidence (derivation_confidence)
                )
                '''
            )
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.claim_balance_diagnostics_table} (
                    claim_balance_diagnostic_id VARCHAR(255) NOT NULL,
                    normalized_event_id VARCHAR(255) NOT NULL,
                    pool_application_id VARCHAR(256) NOT NULL,
                    execution_chain_id VARCHAR(64) NOT NULL,
                    diagnostic_type VARCHAR(64) NOT NULL,
                    derivation_source VARCHAR(64) NOT NULL,
                    derivation_confidence VARCHAR(32) NOT NULL,
                    block_hash VARCHAR(64) NULL,
                    block_height BIGINT NULL,
                    transaction_index INT NULL,
                    message_index INT NULL,
                    rejected BOOLEAN NOT NULL DEFAULT FALSE,
                    source_event_key VARCHAR(255) NOT NULL,
                    event_payload_json LONGTEXT NOT NULL,
                    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    PRIMARY KEY (claim_balance_diagnostic_id),
                    KEY idx_claim_balance_diagnostic_pool (pool_application_id(128), execution_chain_id),
                    KEY idx_claim_balance_diagnostic_source_event (source_event_key),
                    KEY idx_claim_balance_diagnostic_confidence (derivation_confidence)
                )
                '''
            )
            cursor.execute(
                f'''
                ALTER TABLE {self.claim_balance_deltas_table}
                MODIFY COLUMN claim_balance_delta_id VARCHAR(512) NOT NULL
                '''
            )

            self.connection.commit()
        finally:
            cursor.close()

    def delete_correlated_claim_balance_deltas_for_events(
        self,
        *,
        normalized_event_ids: set[str],
    ) -> int:
        if not normalized_event_ids:
            return 0
        cursor = self.cursor()
        try:
            event_placeholders = ', '.join(['%s'] * len(normalized_event_ids))
            cursor.execute(
                f'''
                DELETE FROM {self.claim_balance_deltas_table}
                WHERE normalized_event_id IN ({event_placeholders})
                  AND derivation_source LIKE 'correlated\\_%'
                ''',
                tuple(sorted(normalized_event_ids)),
            )
            self.connection.commit()
            return getattr(cursor, 'rowcount', 0)
        finally:
            cursor.close()

    def upsert_claim_balance_deltas(self, deltas: list[dict[str, object]]) -> int:
        if not deltas:
            return 0
        cursor = self.cursor()
        try:
            for delta in deltas:
                cursor.execute(
                    f'''
                    INSERT INTO {self.claim_balance_deltas_table} (
                        claim_balance_delta_id,
                        normalized_event_id,
                        pool_application_id,
                        execution_chain_id,
                        token,
                        owner,
                        balance_kind,
                        delta_amount,
                        delta_direction,
                        block_hash,
                        block_height,
                        transaction_index,
                        message_index,
                        rejected,
                        derivation_source,
                        derivation_confidence,
                        source_event_key,
                        event_payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pool_application_id = VALUES(pool_application_id),
                        execution_chain_id = VALUES(execution_chain_id),
                        token = VALUES(token),
                        owner = VALUES(owner),
                        balance_kind = VALUES(balance_kind),
                        delta_amount = VALUES(delta_amount),
                        delta_direction = VALUES(delta_direction),
                        block_hash = VALUES(block_hash),
                        block_height = VALUES(block_height),
                        transaction_index = VALUES(transaction_index),
                        message_index = VALUES(message_index),
                        rejected = VALUES(rejected),
                        derivation_source = VALUES(derivation_source),
                        derivation_confidence = VALUES(derivation_confidence),
                        source_event_key = VALUES(source_event_key),
                        event_payload_json = VALUES(event_payload_json)
                    ''',
                    (
                        delta['claim_balance_delta_id'],
                        delta['normalized_event_id'],
                        delta['pool_application_id'],
                        delta['execution_chain_id'],
                        delta['token'],
                        delta['owner'],
                        delta['balance_kind'],
                        delta['delta_amount'],
                        delta['delta_direction'],
                        delta.get('block_hash'),
                        delta.get('block_height'),
                        delta.get('transaction_index'),
                        delta.get('message_index'),
                        bool(delta.get('rejected', False)),
                        delta['derivation_source'],
                        delta['derivation_confidence'],
                        delta['source_event_key'],
                        self.fingerprint.build_json(delta.get('event_payload_json') or {}),
                    ),
                )
            self.connection.commit()
            return len(deltas)
        finally:
            cursor.close()

    def upsert_claim_balance_diagnostics(self, diagnostics: list[dict[str, object]]) -> int:
        if not diagnostics:
            return 0
        cursor = self.cursor()
        try:
            for diagnostic in diagnostics:
                cursor.execute(
                    f'''
                    INSERT INTO {self.claim_balance_diagnostics_table} (
                        claim_balance_diagnostic_id,
                        normalized_event_id,
                        pool_application_id,
                        execution_chain_id,
                        diagnostic_type,
                        derivation_source,
                        derivation_confidence,
                        block_hash,
                        block_height,
                        transaction_index,
                        message_index,
                        rejected,
                        source_event_key,
                        event_payload_json
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pool_application_id = VALUES(pool_application_id),
                        execution_chain_id = VALUES(execution_chain_id),
                        diagnostic_type = VALUES(diagnostic_type),
                        derivation_source = VALUES(derivation_source),
                        derivation_confidence = VALUES(derivation_confidence),
                        block_hash = VALUES(block_hash),
                        block_height = VALUES(block_height),
                        transaction_index = VALUES(transaction_index),
                        message_index = VALUES(message_index),
                        rejected = VALUES(rejected),
                        source_event_key = VALUES(source_event_key),
                        event_payload_json = VALUES(event_payload_json)
                    ''',
                    (
                        diagnostic['claim_balance_diagnostic_id'],
                        diagnostic['normalized_event_id'],
                        diagnostic['pool_application_id'],
                        diagnostic['execution_chain_id'],
                        diagnostic['diagnostic_type'],
                        diagnostic['derivation_source'],
                        diagnostic['derivation_confidence'],
                        diagnostic.get('block_hash'),
                        diagnostic.get('block_height'),
                        diagnostic.get('transaction_index'),
                        diagnostic.get('message_index'),
                        bool(diagnostic.get('rejected', False)),
                        diagnostic['source_event_key'],
                        self.fingerprint.build_json(diagnostic.get('event_payload_json') or {}),
                    ),
                )
            self.connection.commit()
            return len(diagnostics)
        finally:
            cursor.close()

    def delete_claim_balance_diagnostics_for_events(
        self,
        *,
        normalized_event_ids: set[str],
        diagnostic_types: set[str],
    ) -> int:
        if not normalized_event_ids or not diagnostic_types:
            return 0
        cursor = self.cursor()
        try:
            event_placeholders = ', '.join(['%s'] * len(normalized_event_ids))
            type_placeholders = ', '.join(['%s'] * len(diagnostic_types))
            cursor.execute(
                f'''
                DELETE FROM {self.claim_balance_diagnostics_table}
                WHERE normalized_event_id IN ({event_placeholders})
                  AND diagnostic_type IN ({type_placeholders})
                ''',
                tuple(sorted(normalized_event_ids)) + tuple(sorted(diagnostic_types)),
            )
            self.connection.commit()
            return getattr(cursor, 'rowcount', 0)
        finally:
            cursor.close()

    def list_claim_balance_deltas(self, *, pool_application_id: str | None = None) -> list[dict[str, object]]:
        cursor = self.cursor(dictionary=True)
        try:
            params = []
            where = ''
            if pool_application_id:
                where = 'WHERE pool_application_id = %s'
                params.append(pool_application_id)
            cursor.execute(
                f'''
                SELECT
                    claim_balance_delta_id,
                    normalized_event_id,
                    pool_application_id,
                    execution_chain_id,
                    token,
                    owner,
                    balance_kind,
                    delta_amount,
                    delta_direction,
                    block_hash,
                    block_height,
                    transaction_index,
                    message_index,
                    rejected,
                    derivation_source,
                    derivation_confidence,
                    source_event_key,
                    event_payload_json
                FROM {self.claim_balance_deltas_table}
                {where}
                ORDER BY block_height ASC, transaction_index ASC, message_index ASC, claim_balance_delta_id ASC
                ''',
                tuple(params),
            )
            return [self._decode_json(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def list_claim_balance_diagnostics(self, *, pool_application_id: str | None = None) -> list[dict[str, object]]:
        cursor = self.cursor(dictionary=True)
        try:
            params = []
            where = ''
            if pool_application_id:
                where = 'WHERE pool_application_id = %s'
                params.append(pool_application_id)
            cursor.execute(
                f'''
                SELECT
                    claim_balance_diagnostic_id,
                    normalized_event_id,
                    pool_application_id,
                    execution_chain_id,
                    diagnostic_type,
                    derivation_source,
                    derivation_confidence,
                    block_hash,
                    block_height,
                    transaction_index,
                    message_index,
                    rejected,
                    source_event_key,
                    event_payload_json
                FROM {self.claim_balance_diagnostics_table}
                {where}
                ORDER BY block_height ASC, transaction_index ASC, message_index ASC, claim_balance_diagnostic_id ASC
                ''',
                tuple(params),
            )
            return [self._decode_json(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def get_claim_balances(self, *, owner: str) -> list[dict[str, object]]:
        cursor = self.cursor(dictionary=True)
        try:
            cursor.execute(
                f"""
                SELECT
                    deltas.pool_application_id,
                    deltas.execution_chain_id,
                    deltas.token,
                    deltas.owner,
                    GREATEST(COALESCE(SUM(CASE
                        WHEN deltas.balance_kind = 'claimable' AND deltas.delta_direction = 'credit' THEN CAST(deltas.delta_amount AS DECIMAL(65, 0))
                        WHEN deltas.balance_kind = 'claimable' AND deltas.delta_direction = 'debit' THEN -CAST(deltas.delta_amount AS DECIMAL(65, 0))
                        ELSE 0
                    END), 0), 0) / {self.DISPLAY_AMOUNT_SCALE} AS claimable_amount,
                    GREATEST(COALESCE(SUM(CASE
                        WHEN deltas.balance_kind = 'claiming' AND deltas.delta_direction = 'credit' THEN CAST(deltas.delta_amount AS DECIMAL(65, 0))
                        WHEN deltas.balance_kind = 'claiming' AND deltas.delta_direction = 'debit' THEN -CAST(deltas.delta_amount AS DECIMAL(65, 0))
                        ELSE 0
                    END), 0), 0) / {self.DISPLAY_AMOUNT_SCALE} AS claiming_amount,
                    MAX(deltas.block_height) AS latest_block_height,
                    MAX(deltas.transaction_index) AS latest_transaction_index,
                    MAX(deltas.message_index) AS latest_message_index,
                    CASE
                        WHEN COALESCE(MAX(incomplete_diagnostics.incomplete_count), 0) > 0 THEN 'incomplete'
                        ELSE 'complete'
                    END AS projection_status,
                    COALESCE(MAX(incomplete_diagnostics.incomplete_count), 0) AS incomplete_diagnostic_count
                FROM {self.claim_balance_deltas_table} deltas
                LEFT JOIN (
                    SELECT
                        pool_application_id,
                        execution_chain_id,
                        COUNT(*) AS incomplete_count
                    FROM {self.claim_balance_diagnostics_table}
                    WHERE diagnostic_type IN (
                        'claim_delta_requires_new_transaction_correlation',
                        'ambiguous_new_transaction_correlation',
                        'missing_pool_token_metadata'
                    )
                    GROUP BY pool_application_id, execution_chain_id
                ) incomplete_diagnostics
                  ON incomplete_diagnostics.pool_application_id = deltas.pool_application_id
                 AND incomplete_diagnostics.execution_chain_id = deltas.execution_chain_id
                WHERE deltas.owner = %s
                GROUP BY deltas.pool_application_id, deltas.execution_chain_id, deltas.token, deltas.owner
                HAVING claimable_amount <> 0 OR claiming_amount <> 0 OR projection_status = 'incomplete'
                ORDER BY deltas.pool_application_id ASC, deltas.execution_chain_id ASC, deltas.token ASC
                """,
                (owner,),
            )
            return [self._decode_claim_balance_row(row) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def _decode_claim_balance_row(self, row: dict[str, object]) -> dict[str, object]:
        decoded = dict(row)
        decoded['claimable_amount'] = str(decoded.get('claimable_amount', '0'))
        decoded['claiming_amount'] = str(decoded.get('claiming_amount', '0'))
        decoded['projection_status'] = str(decoded.get('projection_status') or 'complete')
        decoded['diagnostics'] = {
            'incomplete_count': int(decoded.pop('incomplete_diagnostic_count') or 0),
        }
        return decoded

    def _decode_json(self, row: dict[str, object]) -> dict[str, object]:
        decoded = dict(row)
        payload = decoded.get('event_payload_json')
        if isinstance(payload, str):
            decoded['event_payload_json'] = json.loads(payload)
        return decoded
