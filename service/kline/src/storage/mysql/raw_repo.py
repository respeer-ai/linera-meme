class RawRepository:
    """Owns Layer 1 observability schema creation and raw-table access boundaries."""

    def __init__(self, connection):
        self.connection = connection
        self.chain_cursors_table = 'chain_cursors'
        self.raw_blocks_table = 'raw_blocks'
        self.raw_incoming_bundles_table = 'raw_incoming_bundles'
        self.raw_posted_messages_table = 'raw_posted_messages'
        self.raw_operations_table = 'raw_operations'
        self.raw_outgoing_messages_table = 'raw_outgoing_messages'
        self.raw_events_table = 'raw_events'
        self.raw_oracle_responses_table = 'raw_oracle_responses'
        self.processing_cursors_table = 'processing_cursors'
        self.ingestion_anomalies_table = 'ingestion_anomalies'
        self.raw_block_ingest_runs_table = 'raw_block_ingest_runs'

    def ordered_schema_definitions(self) -> list[tuple[str, str]]:
        return [
            (
                self.chain_cursors_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.chain_cursors_table} (
                    chain_id VARCHAR(64) NOT NULL,
                    last_finalized_height BIGINT NULL,
                    last_finalized_block_hash VARCHAR(64) NULL,
                    last_attempted_height BIGINT NULL,
                    last_attempted_at DATETIME(6) NULL,
                    last_success_at DATETIME(6) NULL,
                    sync_status VARCHAR(32) NOT NULL,
                    consecutive_failures INT NOT NULL DEFAULT 0,
                    last_error TEXT NULL,
                    updated_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (chain_id)
                )
                ''',
            ),
            (
                self.raw_blocks_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.raw_blocks_table} (
                    block_hash VARCHAR(64) NOT NULL,
                    chain_id VARCHAR(64) NOT NULL,
                    height BIGINT NOT NULL,
                    timestamp_ms BIGINT NOT NULL,
                    epoch BIGINT NULL,
                    state_hash VARCHAR(64) NULL,
                    previous_block_hash VARCHAR(64) NULL,
                    authenticated_owner VARCHAR(128) NULL,
                    operation_count INT NOT NULL DEFAULT 0,
                    incoming_bundle_count INT NOT NULL DEFAULT 0,
                    message_count INT NOT NULL DEFAULT 0,
                    event_count INT NOT NULL DEFAULT 0,
                    blob_count INT NOT NULL DEFAULT 0,
                    raw_block_bytes LONGBLOB NOT NULL,
                    indexed_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (block_hash),
                    UNIQUE KEY uq_raw_blocks_chain_height (chain_id, height),
                    KEY idx_raw_blocks_chain_timestamp (chain_id, timestamp_ms),
                    KEY idx_raw_blocks_timestamp (timestamp_ms)
                )
                ''',
            ),
            (
                self.raw_incoming_bundles_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.raw_incoming_bundles_table} (
                    bundle_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    target_chain_id VARCHAR(64) NOT NULL,
                    target_block_hash VARCHAR(64) NOT NULL,
                    bundle_index INT NOT NULL,
                    origin_chain_id VARCHAR(64) NOT NULL,
                    action VARCHAR(16) NOT NULL,
                    source_height BIGINT NOT NULL,
                    source_timestamp_ms BIGINT NOT NULL,
                    source_cert_hash VARCHAR(64) NOT NULL,
                    transaction_index INT NOT NULL,
                    indexed_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (bundle_id),
                    UNIQUE KEY uq_raw_incoming_bundles_target (target_block_hash, bundle_index),
                    KEY idx_raw_incoming_bundles_source_cert (origin_chain_id, source_cert_hash, transaction_index),
                    KEY idx_raw_incoming_bundles_target_chain (target_chain_id, source_height),
                    KEY idx_raw_incoming_bundles_action (action),
                    CONSTRAINT fk_raw_incoming_bundles_block
                        FOREIGN KEY (target_block_hash) REFERENCES {self.raw_blocks_table}(block_hash)
                )
                ''',
            ),
            (
                self.raw_posted_messages_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.raw_posted_messages_table} (
                    posted_message_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    bundle_id BIGINT UNSIGNED NOT NULL,
                    origin_chain_id VARCHAR(64) NOT NULL,
                    source_cert_hash VARCHAR(64) NOT NULL,
                    transaction_index INT NOT NULL,
                    message_index INT NOT NULL,
                    authenticated_owner VARCHAR(128) NULL,
                    grant_amount VARCHAR(64) NULL,
                    refund_grant_to VARCHAR(128) NULL,
                    message_kind VARCHAR(32) NOT NULL,
                    message_type VARCHAR(16) NOT NULL,
                    application_id VARCHAR(128) NULL,
                    system_message_type VARCHAR(64) NULL,
                    system_target VARCHAR(128) NULL,
                    system_amount VARCHAR(64) NULL,
                    system_source VARCHAR(128) NULL,
                    system_owner VARCHAR(128) NULL,
                    system_recipient VARCHAR(128) NULL,
                    raw_message_bytes LONGBLOB NOT NULL,
                    indexed_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (posted_message_id),
                    UNIQUE KEY uq_raw_posted_messages_bundle (bundle_id, message_index),
                    UNIQUE KEY uq_raw_posted_messages_external (origin_chain_id, source_cert_hash, transaction_index, message_index),
                    KEY idx_raw_posted_messages_app (application_id),
                    KEY idx_raw_posted_messages_type (message_type, system_message_type),
                    CONSTRAINT fk_raw_posted_messages_bundle
                        FOREIGN KEY (bundle_id) REFERENCES {self.raw_incoming_bundles_table}(bundle_id)
                )
                ''',
            ),
            (
                self.raw_operations_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.raw_operations_table} (
                    operation_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    block_hash VARCHAR(64) NOT NULL,
                    chain_id VARCHAR(64) NOT NULL,
                    height BIGINT NOT NULL,
                    operation_index INT NOT NULL,
                    operation_type VARCHAR(16) NOT NULL,
                    application_id VARCHAR(128) NULL,
                    system_operation_type VARCHAR(64) NULL,
                    authenticated_owner VARCHAR(128) NULL,
                    raw_operation_bytes LONGBLOB NOT NULL,
                    indexed_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (operation_id),
                    UNIQUE KEY uq_raw_operations_block_index (block_hash, operation_index),
                    KEY idx_raw_operations_app (application_id),
                    KEY idx_raw_operations_chain_height (chain_id, height),
                    CONSTRAINT fk_raw_operations_block
                        FOREIGN KEY (block_hash) REFERENCES {self.raw_blocks_table}(block_hash)
                )
                ''',
            ),
            (
                self.raw_outgoing_messages_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.raw_outgoing_messages_table} (
                    outgoing_message_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    block_hash VARCHAR(64) NOT NULL,
                    chain_id VARCHAR(64) NOT NULL,
                    height BIGINT NOT NULL,
                    transaction_index INT NOT NULL,
                    message_index INT NOT NULL,
                    destination_chain_id VARCHAR(64) NOT NULL,
                    authenticated_owner VARCHAR(128) NULL,
                    grant_amount VARCHAR(64) NULL,
                    message_kind VARCHAR(32) NOT NULL,
                    message_type VARCHAR(16) NOT NULL,
                    application_id VARCHAR(128) NULL,
                    system_message_type VARCHAR(64) NULL,
                    system_target VARCHAR(128) NULL,
                    system_amount VARCHAR(64) NULL,
                    system_source VARCHAR(128) NULL,
                    system_owner VARCHAR(128) NULL,
                    system_recipient VARCHAR(128) NULL,
                    raw_message_bytes LONGBLOB NOT NULL,
                    indexed_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (outgoing_message_id),
                    UNIQUE KEY uq_raw_outgoing_messages_block_tx_msg (block_hash, transaction_index, message_index),
                    KEY idx_raw_outgoing_messages_destination (destination_chain_id),
                    KEY idx_raw_outgoing_messages_app (application_id),
                    CONSTRAINT fk_raw_outgoing_messages_block
                        FOREIGN KEY (block_hash) REFERENCES {self.raw_blocks_table}(block_hash)
                )
                ''',
            ),
            (
                self.raw_events_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.raw_events_table} (
                    event_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    block_hash VARCHAR(64) NOT NULL,
                    chain_id VARCHAR(64) NOT NULL,
                    height BIGINT NOT NULL,
                    transaction_index INT NOT NULL,
                    event_index INT NOT NULL,
                    stream_id VARCHAR(255) NOT NULL,
                    stream_index BIGINT NOT NULL,
                    raw_event_bytes LONGBLOB NOT NULL,
                    indexed_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (event_id),
                    UNIQUE KEY uq_raw_events_block_tx_event (block_hash, transaction_index, event_index),
                    KEY idx_raw_events_stream (stream_id, stream_index),
                    KEY idx_raw_events_chain_height (chain_id, height),
                    CONSTRAINT fk_raw_events_block
                        FOREIGN KEY (block_hash) REFERENCES {self.raw_blocks_table}(block_hash)
                )
                ''',
            ),
            (
                self.raw_oracle_responses_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.raw_oracle_responses_table} (
                    oracle_response_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    block_hash VARCHAR(64) NOT NULL,
                    chain_id VARCHAR(64) NOT NULL,
                    height BIGINT NOT NULL,
                    transaction_index INT NOT NULL,
                    response_index INT NOT NULL,
                    response_type VARCHAR(64) NOT NULL,
                    blob_hash VARCHAR(64) NULL,
                    raw_response_bytes LONGBLOB NULL,
                    indexed_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (oracle_response_id),
                    UNIQUE KEY uq_raw_oracle_responses_block_tx_response (block_hash, transaction_index, response_index),
                    KEY idx_raw_oracle_responses_blob (blob_hash),
                    KEY idx_raw_oracle_responses_chain_height (chain_id, height),
                    CONSTRAINT fk_raw_oracle_responses_block
                        FOREIGN KEY (block_hash) REFERENCES {self.raw_blocks_table}(block_hash)
                )
                ''',
            ),
            (
                self.processing_cursors_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.processing_cursors_table} (
                    cursor_name VARCHAR(128) NOT NULL,
                    cursor_scope VARCHAR(64) NOT NULL,
                    partition_key VARCHAR(255) NOT NULL,
                    last_sequence VARCHAR(255) NULL,
                    last_block_hash VARCHAR(64) NULL,
                    last_success_at DATETIME(6) NULL,
                    last_attempt_at DATETIME(6) NULL,
                    status VARCHAR(32) NOT NULL,
                    consecutive_failures INT NOT NULL DEFAULT 0,
                    last_error TEXT NULL,
                    updated_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (cursor_name, partition_key)
                )
                ''',
            ),
            (
                self.ingestion_anomalies_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.ingestion_anomalies_table} (
                    anomaly_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    anomaly_type VARCHAR(64) NOT NULL,
                    severity VARCHAR(16) NOT NULL,
                    chain_id VARCHAR(64) NULL,
                    height BIGINT NULL,
                    block_hash VARCHAR(64) NULL,
                    object_type VARCHAR(64) NOT NULL,
                    object_identity VARCHAR(255) NOT NULL,
                    expected_fingerprint VARCHAR(128) NULL,
                    observed_fingerprint VARCHAR(128) NULL,
                    details_json JSON NULL,
                    first_seen_at DATETIME(6) NOT NULL,
                    last_seen_at DATETIME(6) NOT NULL,
                    occurrence_count INT NOT NULL DEFAULT 1,
                    status VARCHAR(32) NOT NULL,
                    PRIMARY KEY (anomaly_id),
                    UNIQUE KEY uq_ingestion_anomaly_identity (anomaly_type, object_type, object_identity),
                    KEY idx_ingestion_anomalies_chain_height (chain_id, height),
                    KEY idx_ingestion_anomalies_status (status, severity, last_seen_at)
                )
                ''',
            ),
            (
                self.raw_block_ingest_runs_table,
                f'''
                CREATE TABLE IF NOT EXISTS {self.raw_block_ingest_runs_table} (
                    run_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
                    chain_id VARCHAR(64) NOT NULL,
                    height BIGINT NOT NULL,
                    mode VARCHAR(32) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    block_hash VARCHAR(64) NULL,
                    started_at DATETIME(6) NOT NULL,
                    finished_at DATETIME(6) NULL,
                    error_text TEXT NULL,
                    summary_json JSON NULL,
                    PRIMARY KEY (run_id),
                    KEY idx_raw_block_ingest_runs_chain_height (chain_id, height, started_at),
                    KEY idx_raw_block_ingest_runs_status (status, started_at)
                )
                ''',
            ),
        ]

    def ensure_schema(self):
        cursor = self.connection.cursor()
        try:
            for _table_name, ddl in self.ordered_schema_definitions():
                cursor.execute(ddl)
            self.connection.commit()
        finally:
            cursor.close()

    def load_chain_cursor(self, chain_id: str) -> dict | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT
                    chain_id,
                    last_finalized_height,
                    last_finalized_block_hash,
                    last_attempted_height,
                    sync_status,
                    consecutive_failures,
                    last_error
                FROM {self.chain_cursors_table}
                WHERE chain_id = %s
                ''',
                (chain_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            cursor.close()

    def mark_attempt(self, chain_id: str, height: int) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {self.chain_cursors_table}
                (
                    chain_id,
                    last_finalized_height,
                    last_finalized_block_hash,
                    last_attempted_height,
                    last_attempted_at,
                    last_success_at,
                    sync_status,
                    consecutive_failures,
                    last_error,
                    updated_at
                )
                VALUES (%s, NULL, NULL, %s, UTC_TIMESTAMP(6), NULL, %s, 0, NULL, UTC_TIMESTAMP(6))
                ON DUPLICATE KEY UPDATE
                    last_attempted_height = VALUES(last_attempted_height),
                    last_attempted_at = UTC_TIMESTAMP(6),
                    sync_status = VALUES(sync_status),
                    updated_at = UTC_TIMESTAMP(6)
                ''',
                (chain_id, int(height), 'syncing'),
            )
            self.connection.commit()
        finally:
            cursor.close()

    def mark_failure(self, chain_id: str, height: int, error_text: str) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {self.chain_cursors_table}
                (
                    chain_id,
                    last_finalized_height,
                    last_finalized_block_hash,
                    last_attempted_height,
                    last_attempted_at,
                    last_success_at,
                    sync_status,
                    consecutive_failures,
                    last_error,
                    updated_at
                )
                VALUES (%s, NULL, NULL, %s, UTC_TIMESTAMP(6), NULL, %s, 1, %s, UTC_TIMESTAMP(6))
                ON DUPLICATE KEY UPDATE
                    last_attempted_height = VALUES(last_attempted_height),
                    last_attempted_at = UTC_TIMESTAMP(6),
                    sync_status = VALUES(sync_status),
                    consecutive_failures = consecutive_failures + 1,
                    last_error = VALUES(last_error),
                    updated_at = UTC_TIMESTAMP(6)
                ''',
                (chain_id, int(height), 'error', error_text),
            )
            self.connection.commit()
        finally:
            cursor.close()

    def record_anomaly(
        self,
        *,
        anomaly_type: str,
        object_type: str,
        object_identity: str,
        severity: str = 'error',
        chain_id: str | None = None,
        height: int | None = None,
        block_hash: str | None = None,
        expected_fingerprint: str | None = None,
        observed_fingerprint: str | None = None,
        details_json: str | None = None,
        status: str = 'open',
    ) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {self.ingestion_anomalies_table}
                (
                    anomaly_type,
                    severity,
                    chain_id,
                    height,
                    block_hash,
                    object_type,
                    object_identity,
                    expected_fingerprint,
                    observed_fingerprint,
                    details_json,
                    first_seen_at,
                    last_seen_at,
                    occurrence_count,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1, %s)
                ON DUPLICATE KEY UPDATE
                    last_seen_at = UTC_TIMESTAMP(6),
                    occurrence_count = occurrence_count + 1,
                    observed_fingerprint = VALUES(observed_fingerprint),
                    details_json = VALUES(details_json),
                    status = VALUES(status)
                ''',
                (
                    anomaly_type,
                    severity,
                    chain_id,
                    None if height is None else int(height),
                    block_hash,
                    object_type,
                    object_identity,
                    expected_fingerprint,
                    observed_fingerprint,
                    details_json,
                    status,
                ),
            )
            self.connection.commit()
        finally:
            cursor.close()

    def ingest_block(self, block: dict, mode: str = 'live') -> dict:
        chain_id = str(block['chain_id'])
        height = int(block['height'])
        block_hash = str(block['block_hash'])
        raw_block_bytes = block.get('raw_block_bytes')
        if raw_block_bytes is None:
            raw_block_bytes = str(block).encode()

        existing = self.load_chain_cursor(chain_id)
        if existing is not None:
            last_height = existing.get('last_finalized_height')
            if last_height is not None and height <= int(last_height):
                return {
                    'chain_id': chain_id,
                    'height': height,
                    'block_hash': block_hash,
                    'ingest_status': 'already_finalized',
                    'cursor_advanced': False,
                }

        anomaly_to_record = None
        read_cursor = self.connection.cursor(dictionary=True)
        write_cursor = self.connection.cursor()
        try:
            self._begin_transaction()
            read_cursor.execute(
                f'''
                SELECT block_hash
                FROM {self.raw_blocks_table}
                WHERE chain_id = %s AND height = %s
                ''',
                (chain_id, height),
            )
            existing_block = read_cursor.fetchone()
            if existing_block is not None:
                existing_hash = existing_block['block_hash']
                if existing_hash != block_hash:
                    anomaly_to_record = {
                        'anomaly_type': 'block_hash_mismatch',
                        'object_type': 'raw_block',
                        'object_identity': f'{chain_id}:{height}',
                        'chain_id': chain_id,
                        'height': height,
                        'block_hash': block_hash,
                        'expected_fingerprint': existing_hash,
                        'observed_fingerprint': block_hash,
                        'details_json': str(block),
                    }
                    raise ValueError(f'Conflicting block hash for {chain_id}@{height}')
            else:
                write_cursor.execute(
                    f'''
                    INSERT INTO {self.raw_blocks_table}
                    (
                        block_hash,
                        chain_id,
                        height,
                        timestamp_ms,
                        epoch,
                        state_hash,
                        previous_block_hash,
                        authenticated_owner,
                        operation_count,
                        incoming_bundle_count,
                        message_count,
                        event_count,
                        blob_count,
                        raw_block_bytes,
                        indexed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6))
                    ''',
                    (
                        block_hash,
                        chain_id,
                        height,
                        int(block.get('timestamp_ms', 0)),
                        block.get('epoch'),
                        block.get('state_hash'),
                        block.get('previous_block_hash'),
                        block.get('authenticated_owner'),
                        int(block.get('operation_count', 0)),
                        int(block.get('incoming_bundle_count', 0)),
                        int(block.get('message_count', 0)),
                        int(block.get('event_count', 0)),
                        int(block.get('blob_count', 0)),
                        raw_block_bytes,
                    ),
                )

            self._insert_incoming_bundles(read_cursor, write_cursor, block)
            self._insert_operations(read_cursor, write_cursor, block)
            self._insert_outgoing_messages(read_cursor, write_cursor, block)
            self._insert_events(read_cursor, write_cursor, block)
            self._insert_oracle_responses(read_cursor, write_cursor, block)

            write_cursor.execute(
                f'''
                INSERT INTO {self.chain_cursors_table}
                (
                    chain_id,
                    last_finalized_height,
                    last_finalized_block_hash,
                    last_attempted_height,
                    last_attempted_at,
                    last_success_at,
                    sync_status,
                    consecutive_failures,
                    last_error,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), %s, 0, NULL, UTC_TIMESTAMP(6))
                ON DUPLICATE KEY UPDATE
                    last_finalized_height = VALUES(last_finalized_height),
                    last_finalized_block_hash = VALUES(last_finalized_block_hash),
                    last_attempted_height = VALUES(last_attempted_height),
                    last_attempted_at = UTC_TIMESTAMP(6),
                    last_success_at = UTC_TIMESTAMP(6),
                    sync_status = VALUES(sync_status),
                    consecutive_failures = 0,
                    last_error = NULL,
                    updated_at = UTC_TIMESTAMP(6)
                ''',
                (chain_id, height, block_hash, height, 'idle'),
            )

            write_cursor.execute(
                f'''
                INSERT INTO {self.raw_block_ingest_runs_table}
                (
                    chain_id,
                    height,
                    mode,
                    status,
                    block_hash,
                    started_at,
                    finished_at,
                    error_text,
                    summary_json
                )
                VALUES (%s, %s, %s, %s, %s, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), NULL, %s)
                ''',
                (
                    chain_id,
                    height,
                    mode,
                    'success',
                    block_hash,
                    str({
                        'operation_count': int(block.get('operation_count', 0)),
                        'incoming_bundle_count': int(block.get('incoming_bundle_count', 0)),
                    }),
                ),
            )
            self.connection.commit()
            return {
                'chain_id': chain_id,
                'height': height,
                'block_hash': block_hash,
                'ingest_status': 'ingested',
                'cursor_advanced': True,
            }
        except Exception:
            self._rollback_transaction()
            if anomaly_to_record is not None:
                self.record_anomaly(**anomaly_to_record)
            raise
        finally:
            read_cursor.close()
            write_cursor.close()

    def _insert_incoming_bundles(self, read_cursor, write_cursor, block: dict) -> None:
        for bundle_index, bundle in enumerate(block.get('incoming_bundles', [])):
            key_bundle_index = int(bundle.get('bundle_index', bundle_index))
            bundle_fingerprint = self._fingerprint({
                'origin_chain_id': str(bundle['origin_chain_id']),
                'action': str(bundle.get('action', 'Accept')),
                'source_height': int(bundle.get('source_height', 0)),
                'source_timestamp_ms': int(bundle.get('source_timestamp_ms', 0)),
                'source_cert_hash': str(bundle.get('source_cert_hash', '')),
                'transaction_index': int(bundle.get('transaction_index', 0)),
            })
            existing_bundle_id = self._select_existing_identity(
                read_cursor=read_cursor,
                table_name=self.raw_incoming_bundles_table,
                select_columns=(
                    'bundle_id',
                    'origin_chain_id',
                    'action',
                    'source_height',
                    'source_timestamp_ms',
                    'source_cert_hash',
                    'transaction_index',
                ),
                where_columns=(
                    ('target_block_hash', str(block['block_hash'])),
                    ('bundle_index', key_bundle_index),
                ),
            )
            if existing_bundle_id is None:
                write_cursor.execute(
                    f'''
                    INSERT INTO {self.raw_incoming_bundles_table}
                    (
                        target_chain_id,
                        target_block_hash,
                        bundle_index,
                        origin_chain_id,
                        action,
                        source_height,
                        source_timestamp_ms,
                        source_cert_hash,
                        transaction_index,
                        indexed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6))
                    ''',
                    (
                        str(block['chain_id']),
                        str(block['block_hash']),
                        key_bundle_index,
                        str(bundle['origin_chain_id']),
                        str(bundle.get('action', 'Accept')),
                        int(bundle.get('source_height', 0)),
                        int(bundle.get('source_timestamp_ms', 0)),
                        str(bundle.get('source_cert_hash', '')),
                        int(bundle.get('transaction_index', 0)),
                    ),
                )
                bundle_id = write_cursor.lastrowid
            else:
                existing_bundle_fingerprint = self._fingerprint({
                    'origin_chain_id': existing_bundle_id['origin_chain_id'],
                    'action': existing_bundle_id['action'],
                    'source_height': int(existing_bundle_id['source_height']),
                    'source_timestamp_ms': int(existing_bundle_id['source_timestamp_ms']),
                    'source_cert_hash': existing_bundle_id['source_cert_hash'],
                    'transaction_index': int(existing_bundle_id['transaction_index']),
                })
                if existing_bundle_fingerprint != bundle_fingerprint:
                    raise ValueError(f'Conflicting incoming bundle for {block["block_hash"]}:{key_bundle_index}')
                bundle_id = int(existing_bundle_id['bundle_id'])
            for message_index, message in enumerate(bundle.get('posted_messages', [])):
                key_message_index = int(message.get('message_index', message_index))
                message_fingerprint = self._fingerprint({
                    'origin_chain_id': str(message.get('origin_chain_id', bundle['origin_chain_id'])),
                    'source_cert_hash': str(message.get('source_cert_hash', bundle.get('source_cert_hash', ''))),
                    'transaction_index': int(message.get('transaction_index', bundle.get('transaction_index', 0))),
                    'authenticated_owner': message.get('authenticated_owner'),
                    'grant_amount': message.get('grant_amount'),
                    'refund_grant_to': message.get('refund_grant_to'),
                    'message_kind': str(message.get('message_kind', 'Simple')),
                    'message_type': str(message.get('message_type', 'User')),
                    'application_id': message.get('application_id'),
                    'system_message_type': message.get('system_message_type'),
                    'system_target': message.get('system_target'),
                    'system_amount': message.get('system_amount'),
                    'system_source': message.get('system_source'),
                    'system_owner': message.get('system_owner'),
                    'system_recipient': message.get('system_recipient'),
                    'raw_message_bytes': message.get('raw_message_bytes', b''),
                })
                existing_message = self._select_existing_identity(
                    read_cursor=read_cursor,
                    table_name=self.raw_posted_messages_table,
                    select_columns=(
                        'origin_chain_id',
                        'source_cert_hash',
                        'transaction_index',
                        'authenticated_owner',
                        'grant_amount',
                        'refund_grant_to',
                        'message_kind',
                        'message_type',
                        'application_id',
                        'system_message_type',
                        'system_target',
                        'system_amount',
                        'system_source',
                        'system_owner',
                        'system_recipient',
                        'raw_message_bytes',
                    ),
                    where_columns=(
                        ('bundle_id', bundle_id),
                        ('message_index', key_message_index),
                    ),
                )
                if existing_message is not None:
                    existing_message_fingerprint = self._fingerprint(existing_message)
                    if existing_message_fingerprint != message_fingerprint:
                        raise ValueError(f'Conflicting posted message for bundle {bundle_id}:{key_message_index}')
                    continue
                write_cursor.execute(
                    f'''
                    INSERT INTO {self.raw_posted_messages_table}
                    (
                        bundle_id,
                        origin_chain_id,
                        source_cert_hash,
                        transaction_index,
                        message_index,
                        authenticated_owner,
                        grant_amount,
                        refund_grant_to,
                        message_kind,
                        message_type,
                        application_id,
                        system_message_type,
                        system_target,
                        system_amount,
                        system_source,
                        system_owner,
                        system_recipient,
                        raw_message_bytes,
                        indexed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6))
                    ''',
                    (
                        bundle_id,
                        str(message.get('origin_chain_id', bundle['origin_chain_id'])),
                        str(message.get('source_cert_hash', bundle.get('source_cert_hash', ''))),
                        int(message.get('transaction_index', bundle.get('transaction_index', 0))),
                        key_message_index,
                        message.get('authenticated_owner'),
                        message.get('grant_amount'),
                        message.get('refund_grant_to'),
                        str(message.get('message_kind', 'Simple')),
                        str(message.get('message_type', 'User')),
                        message.get('application_id'),
                        message.get('system_message_type'),
                        message.get('system_target'),
                        message.get('system_amount'),
                        message.get('system_source'),
                        message.get('system_owner'),
                        message.get('system_recipient'),
                        message.get('raw_message_bytes', b''),
                    ),
                )

    def _insert_operations(self, read_cursor, write_cursor, block: dict) -> None:
        for operation_index, operation in enumerate(block.get('operations', [])):
            key_operation_index = int(operation.get('operation_index', operation_index))
            operation_fingerprint = self._fingerprint({
                'operation_type': str(operation.get('operation_type', 'User')),
                'application_id': operation.get('application_id'),
                'system_operation_type': operation.get('system_operation_type'),
                'authenticated_owner': operation.get('authenticated_owner'),
                'raw_operation_bytes': operation.get('raw_operation_bytes', b''),
            })
            existing_operation = self._select_existing_identity(
                read_cursor=read_cursor,
                table_name=self.raw_operations_table,
                select_columns=(
                    'operation_type',
                    'application_id',
                    'system_operation_type',
                    'authenticated_owner',
                    'raw_operation_bytes',
                ),
                where_columns=(
                    ('block_hash', str(block['block_hash'])),
                    ('operation_index', key_operation_index),
                ),
            )
            if existing_operation is not None:
                if self._fingerprint(existing_operation) != operation_fingerprint:
                    raise ValueError(f'Conflicting operation for {block["block_hash"]}:{key_operation_index}')
                continue
            write_cursor.execute(
                f'''
                INSERT INTO {self.raw_operations_table}
                (
                    block_hash,
                    chain_id,
                    height,
                    operation_index,
                    operation_type,
                    application_id,
                    system_operation_type,
                    authenticated_owner,
                    raw_operation_bytes,
                    indexed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6))
                ''',
                (
                    str(block['block_hash']),
                    str(block['chain_id']),
                    int(block['height']),
                    key_operation_index,
                    str(operation.get('operation_type', 'User')),
                    operation.get('application_id'),
                    operation.get('system_operation_type'),
                    operation.get('authenticated_owner'),
                    operation.get('raw_operation_bytes', b''),
                ),
            )

    def _insert_outgoing_messages(self, read_cursor, write_cursor, block: dict) -> None:
        for message_index, message in enumerate(block.get('outgoing_messages', [])):
            key_message_index = int(message.get('message_index', message_index))
            message_fingerprint = self._fingerprint({
                'transaction_index': int(message.get('transaction_index', 0)),
                'destination_chain_id': str(message.get('destination_chain_id', '')),
                'authenticated_owner': message.get('authenticated_owner'),
                'grant_amount': message.get('grant_amount'),
                'message_kind': str(message.get('message_kind', 'Simple')),
                'message_type': str(message.get('message_type', 'User')),
                'application_id': message.get('application_id'),
                'system_message_type': message.get('system_message_type'),
                'system_target': message.get('system_target'),
                'system_amount': message.get('system_amount'),
                'system_source': message.get('system_source'),
                'system_owner': message.get('system_owner'),
                'system_recipient': message.get('system_recipient'),
                'raw_message_bytes': message.get('raw_message_bytes', b''),
            })
            existing_message = self._select_existing_identity(
                read_cursor=read_cursor,
                table_name=self.raw_outgoing_messages_table,
                select_columns=(
                    'transaction_index',
                    'destination_chain_id',
                    'authenticated_owner',
                    'grant_amount',
                    'message_kind',
                    'message_type',
                    'application_id',
                    'system_message_type',
                    'system_target',
                    'system_amount',
                    'system_source',
                    'system_owner',
                    'system_recipient',
                    'raw_message_bytes',
                ),
                where_columns=(
                    ('block_hash', str(block['block_hash'])),
                    ('transaction_index', int(message.get('transaction_index', 0))),
                    ('message_index', key_message_index),
                ),
            )
            if existing_message is not None:
                if self._fingerprint(existing_message) != message_fingerprint:
                    raise ValueError(f'Conflicting outgoing message for {block["block_hash"]}:{key_message_index}')
                continue
            write_cursor.execute(
                f'''
                INSERT INTO {self.raw_outgoing_messages_table}
                (
                    block_hash,
                    chain_id,
                    height,
                    transaction_index,
                    message_index,
                    destination_chain_id,
                    authenticated_owner,
                    grant_amount,
                    message_kind,
                    message_type,
                    application_id,
                    system_message_type,
                    system_target,
                    system_amount,
                    system_source,
                    system_owner,
                    system_recipient,
                    raw_message_bytes,
                    indexed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6))
                ''',
                (
                    str(block['block_hash']),
                    str(block['chain_id']),
                    int(block['height']),
                    int(message.get('transaction_index', 0)),
                    key_message_index,
                    str(message.get('destination_chain_id', '')),
                    message.get('authenticated_owner'),
                    message.get('grant_amount'),
                    str(message.get('message_kind', 'Simple')),
                    str(message.get('message_type', 'User')),
                    message.get('application_id'),
                    message.get('system_message_type'),
                    message.get('system_target'),
                    message.get('system_amount'),
                    message.get('system_source'),
                    message.get('system_owner'),
                    message.get('system_recipient'),
                    message.get('raw_message_bytes', b''),
                ),
            )

    def _insert_events(self, read_cursor, write_cursor, block: dict) -> None:
        for event_index, event in enumerate(block.get('events', [])):
            key_event_index = int(event.get('event_index', event_index))
            event_fingerprint = self._fingerprint({
                'transaction_index': int(event.get('transaction_index', 0)),
                'stream_id': str(event.get('stream_id', '')),
                'stream_index': int(event.get('stream_index', 0)),
                'raw_event_bytes': event.get('raw_event_bytes', b''),
            })
            existing_event = self._select_existing_identity(
                read_cursor=read_cursor,
                table_name=self.raw_events_table,
                select_columns=(
                    'transaction_index',
                    'stream_id',
                    'stream_index',
                    'raw_event_bytes',
                ),
                where_columns=(
                    ('block_hash', str(block['block_hash'])),
                    ('transaction_index', int(event.get('transaction_index', 0))),
                    ('event_index', key_event_index),
                ),
            )
            if existing_event is not None:
                if self._fingerprint(existing_event) != event_fingerprint:
                    raise ValueError(f'Conflicting event for {block["block_hash"]}:{key_event_index}')
                continue
            write_cursor.execute(
                f'''
                INSERT INTO {self.raw_events_table}
                (
                    block_hash,
                    chain_id,
                    height,
                    transaction_index,
                    event_index,
                    stream_id,
                    stream_index,
                    raw_event_bytes,
                    indexed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6))
                ''',
                (
                    str(block['block_hash']),
                    str(block['chain_id']),
                    int(block['height']),
                    int(event.get('transaction_index', 0)),
                    key_event_index,
                    str(event.get('stream_id', '')),
                    int(event.get('stream_index', 0)),
                    event.get('raw_event_bytes', b''),
                ),
            )

    def _insert_oracle_responses(self, read_cursor, write_cursor, block: dict) -> None:
        for response_index, response in enumerate(block.get('oracle_responses', [])):
            key_response_index = int(response.get('response_index', response_index))
            response_fingerprint = self._fingerprint({
                'transaction_index': int(response.get('transaction_index', 0)),
                'response_type': str(response.get('response_type', 'unknown')),
                'blob_hash': response.get('blob_hash'),
                'raw_response_bytes': response.get('raw_response_bytes'),
            })
            existing_response = self._select_existing_identity(
                read_cursor=read_cursor,
                table_name=self.raw_oracle_responses_table,
                select_columns=(
                    'transaction_index',
                    'response_type',
                    'blob_hash',
                    'raw_response_bytes',
                ),
                where_columns=(
                    ('block_hash', str(block['block_hash'])),
                    ('transaction_index', int(response.get('transaction_index', 0))),
                    ('response_index', key_response_index),
                ),
            )
            if existing_response is not None:
                if self._fingerprint(existing_response) != response_fingerprint:
                    raise ValueError(f'Conflicting oracle response for {block["block_hash"]}:{key_response_index}')
                continue
            write_cursor.execute(
                f'''
                INSERT INTO {self.raw_oracle_responses_table}
                (
                    block_hash,
                    chain_id,
                    height,
                    transaction_index,
                    response_index,
                    response_type,
                    blob_hash,
                    raw_response_bytes,
                    indexed_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6))
                ''',
                (
                    str(block['block_hash']),
                    str(block['chain_id']),
                    int(block['height']),
                    int(response.get('transaction_index', 0)),
                    key_response_index,
                    str(response.get('response_type', 'unknown')),
                    response.get('blob_hash'),
                    response.get('raw_response_bytes'),
                ),
            )

    def _begin_transaction(self) -> None:
        if hasattr(self.connection, 'start_transaction'):
            self.connection.start_transaction()

    def _rollback_transaction(self) -> None:
        if hasattr(self.connection, 'rollback'):
            self.connection.rollback()

    def _select_existing_identity(self, *, read_cursor, table_name: str, select_columns: tuple[str, ...], where_columns: tuple[tuple[str, object], ...]):
        where_sql = ' AND '.join(f'{column} = %s' for column, _value in where_columns)
        params = tuple(value for _column, value in where_columns)
        read_cursor.execute(
            f'''
            SELECT {", ".join(select_columns)}
            FROM {table_name}
            WHERE {where_sql}
            ''',
            params,
        )
        row = read_cursor.fetchone()
        if row is None:
            return None
        return dict(row)

    def _fingerprint(self, payload) -> str:
        return repr(payload)
