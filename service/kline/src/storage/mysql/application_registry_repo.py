import json


class ApplicationRegistryRepository:
    """Persists known application identities and metadata for Layer 2 decoding."""

    def __init__(self, connection):
        self.connection = connection
        self.table_name = 'application_registry'

    def ensure_schema(self) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    application_id VARCHAR(128) NOT NULL,
                    app_type VARCHAR(64) NOT NULL,
                    chain_id VARCHAR(64) NULL,
                    creator_chain_id VARCHAR(64) NULL,
                    owner VARCHAR(128) NULL,
                    parent_application_id VARCHAR(128) NULL,
                    abi_version VARCHAR(32) NULL,
                    discovered_from VARCHAR(64) NOT NULL,
                    status VARCHAR(32) NOT NULL,
                    metadata_json JSON NULL,
                    first_seen_at DATETIME(6) NOT NULL,
                    last_seen_at DATETIME(6) NOT NULL,
                    updated_at DATETIME(6) NOT NULL,
                    PRIMARY KEY (application_id),
                    KEY idx_application_registry_type_status (app_type, status),
                    KEY idx_application_registry_creator_chain (creator_chain_id),
                    KEY idx_application_registry_parent (parent_application_id)
                )
                '''
            )
            self.connection.commit()
        finally:
            cursor.close()

    def upsert_application(self, entry: dict) -> None:
        cursor = self.connection.cursor()
        try:
            cursor.execute(
                f'''
                INSERT INTO {self.table_name}
                (
                    application_id,
                    app_type,
                    chain_id,
                    creator_chain_id,
                    owner,
                    parent_application_id,
                    abi_version,
                    discovered_from,
                    status,
                    metadata_json,
                    first_seen_at,
                    last_seen_at,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), UTC_TIMESTAMP(6))
                ON DUPLICATE KEY UPDATE
                    app_type = VALUES(app_type),
                    chain_id = VALUES(chain_id),
                    creator_chain_id = VALUES(creator_chain_id),
                    owner = VALUES(owner),
                    parent_application_id = VALUES(parent_application_id),
                    abi_version = VALUES(abi_version),
                    discovered_from = VALUES(discovered_from),
                    status = VALUES(status),
                    metadata_json = VALUES(metadata_json),
                    last_seen_at = UTC_TIMESTAMP(6),
                    updated_at = UTC_TIMESTAMP(6)
                ''',
                (
                    entry['application_id'],
                    entry['app_type'],
                    entry.get('chain_id'),
                    entry.get('creator_chain_id'),
                    entry.get('owner'),
                    entry.get('parent_application_id'),
                    entry.get('abi_version'),
                    entry.get('discovered_from', 'manual'),
                    entry.get('status', 'active'),
                    self._metadata_json(entry.get('metadata_json')),
                ),
            )
            self.connection.commit()
        finally:
            cursor.close()

    def get_application(self, application_id: str) -> dict | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT
                    application_id,
                    app_type,
                    chain_id,
                    creator_chain_id,
                    owner,
                    parent_application_id,
                    abi_version,
                    discovered_from,
                    status,
                    metadata_json
                FROM {self.table_name}
                WHERE application_id = %s
                ''',
                (application_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return dict(row)
        finally:
            cursor.close()

    def list_applications(self, *, app_type: str | None = None, limit: int = 200) -> list[dict]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            params: list[object] = []
            where_sql = ''
            if app_type is not None:
                where_sql = 'WHERE app_type = %s'
                params.append(app_type)
            params.append(int(limit))
            cursor.execute(
                f'''
                SELECT
                    application_id,
                    app_type,
                    chain_id,
                    creator_chain_id,
                    owner,
                    parent_application_id,
                    abi_version,
                    discovered_from,
                    status,
                    metadata_json
                FROM {self.table_name}
                {where_sql}
                ORDER BY updated_at DESC, application_id ASC
                LIMIT %s
                ''',
                tuple(params),
            )
            return [dict(row) for row in (cursor.fetchall() or [])]
        finally:
            cursor.close()

    def _metadata_json(self, metadata: dict | None) -> str | None:
        if metadata is None:
            return None
        return json.dumps(
            metadata,
            ensure_ascii=True,
            sort_keys=True,
            separators=(',', ':'),
        )
