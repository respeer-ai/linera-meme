import json

from storage.mysql.canonical_fingerprint import CanonicalFingerprint
from normalizer.normalized_event_result import NormalizedEventResult


class NormalizedEventRepository:
    MARKET_DERIVATION_EVENT_FAMILIES = (
        'pool_new_transaction_recorded',
    )

    def __init__(self, connection):
        self.connection = connection
        self.fingerprint = CanonicalFingerprint()
        self.normalized_events_table = 'normalized_events'

    def ensure_schema(self) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.normalized_events_table} (
                    normalized_event_id VARCHAR(255) NOT NULL,
                    raw_fact_id VARCHAR(255) NOT NULL,
                    raw_table VARCHAR(64) NOT NULL,
                    application_id VARCHAR(128) NOT NULL,
                    payload_kind VARCHAR(16) NOT NULL,
                    event_family VARCHAR(64) NOT NULL,
                    event_type VARCHAR(128) NOT NULL,
                    correlation_key VARCHAR(255) NOT NULL,
                    normalization_status VARCHAR(32) NOT NULL,
                    source_chain_id VARCHAR(64) NULL,
                    target_chain_id VARCHAR(64) NULL,
                    source_block_hash VARCHAR(64) NULL,
                    target_block_hash VARCHAR(64) NULL,
                    source_cert_hash VARCHAR(64) NULL,
                    transaction_index INT NULL,
                    message_index INT NULL,
                    app_type VARCHAR(64) NULL,
                    payload_type VARCHAR(128) NULL,
                    decode_status VARCHAR(32) NULL,
                    event_payload_json LONGTEXT NOT NULL,
                    reprocess_reason VARCHAR(64) NULL,
                    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    PRIMARY KEY (normalized_event_id),
                    KEY idx_normalized_events_correlation (correlation_key),
                    KEY idx_normalized_events_application (application_id, event_family),
                    KEY idx_normalized_events_source_cert (source_cert_hash, transaction_index, message_index),
                    KEY idx_normalized_events_target_chain (target_chain_id, normalization_status)
                )
                '''
            )
            self.connection.commit()
        finally:
            cursor.close()

    def upsert_normalized_events(self, events: list[dict[str, object]]) -> int:
        if not events:
            return 0
        cursor = self.connection.cursor()
        try:
            for event in events:
                cursor.execute(
                    f'''
                    INSERT INTO {self.normalized_events_table} (
                        normalized_event_id,
                        raw_fact_id,
                        raw_table,
                        application_id,
                        payload_kind,
                        event_family,
                        event_type,
                        correlation_key,
                        normalization_status,
                        source_chain_id,
                        target_chain_id,
                        source_block_hash,
                        target_block_hash,
                        source_cert_hash,
                        transaction_index,
                        message_index,
                        app_type,
                        payload_type,
                        decode_status,
                        event_payload_json,
                        reprocess_reason
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        correlation_key = VALUES(correlation_key),
                        normalization_status = VALUES(normalization_status),
                        source_chain_id = VALUES(source_chain_id),
                        target_chain_id = VALUES(target_chain_id),
                        source_block_hash = VALUES(source_block_hash),
                        target_block_hash = VALUES(target_block_hash),
                        source_cert_hash = VALUES(source_cert_hash),
                        transaction_index = VALUES(transaction_index),
                        message_index = VALUES(message_index),
                        app_type = VALUES(app_type),
                        payload_type = VALUES(payload_type),
                        decode_status = VALUES(decode_status),
                        event_payload_json = VALUES(event_payload_json),
                        reprocess_reason = VALUES(reprocess_reason)
                    ''',
                    (
                        event['normalized_event_id'],
                        event['raw_fact_id'],
                        event['raw_table'],
                        event['application_id'],
                        event['payload_kind'],
                        event['event_family'],
                        event['event_type'],
                        event['correlation_key'],
                        event['normalization_status'],
                        event.get('source_chain_id'),
                        event.get('target_chain_id'),
                        event.get('source_block_hash'),
                        event.get('target_block_hash'),
                        event.get('source_cert_hash'),
                        event.get('transaction_index'),
                        event.get('message_index'),
                        event.get('app_type'),
                        event.get('payload_type'),
                        event.get('decode_status'),
                        self.fingerprint.build_json(event.get('event_payload_json') or {}),
                        event.get('reprocess_reason'),
                    ),
                )
            self.connection.commit()
            return len(events)
        finally:
            cursor.close()

    def list_market_derivation_candidates(
        self,
        *,
        raw_table: str,
        after_sequence: int | None,
        limit: int,
    ) -> list[dict]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            where_clauses = [
                'raw_table = %s',
                f'event_family IN ({", ".join(["%s"] * len(self.MARKET_DERIVATION_EVENT_FAMILIES))})',
                'normalization_status = %s',
            ]
            params: list[object] = [
                raw_table,
                *self.MARKET_DERIVATION_EVENT_FAMILIES,
                NormalizedEventResult.STATUS_OBSERVED,
            ]
            if after_sequence is not None:
                where_clauses.append('CAST(raw_fact_id AS UNSIGNED) > %s')
                params.append(int(after_sequence))
            params.append(int(limit))
            cursor.execute(
                f'''
                SELECT
                    normalized_event_id,
                    raw_fact_id,
                    raw_table,
                    application_id,
                    payload_kind,
                    event_family,
                    event_type,
                    correlation_key,
                    normalization_status,
                    source_chain_id,
                    target_chain_id,
                    source_block_hash,
                    target_block_hash,
                    source_cert_hash,
                    transaction_index,
                    message_index,
                    app_type,
                    payload_type,
                    decode_status,
                    event_payload_json,
                    reprocess_reason
                FROM {self.normalized_events_table}
                WHERE {' AND '.join(where_clauses)}
                ORDER BY CAST(raw_fact_id AS UNSIGNED) ASC, normalized_event_id ASC
                LIMIT %s
                ''',
                tuple(params),
            )
            rows = cursor.fetchall() or []
            return [self._decode_row(dict(row)) for row in rows]
        finally:
            cursor.close()

    def _decode_row(self, row: dict[str, object]) -> dict[str, object]:
        payload = row.get('event_payload_json')
        if isinstance(payload, str):
            row['event_payload_json'] = json.loads(payload)
        return row
