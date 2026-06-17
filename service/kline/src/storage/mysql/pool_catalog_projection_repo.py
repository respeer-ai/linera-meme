import json
from account_codec import AccountCodec


class PoolCatalogProjectionRepository:
    POOL_CREATED_FAMILIES = {
        'swap_pool_created_recorded',
        'swap_user_pool_created_recorded',
    }

    def __init__(self, db_or_connection, *, current_swap_application_id: str | None = None):
        self.db = db_or_connection if hasattr(db_or_connection, 'ensure_fresh_read_connection') else None
        self.connection = getattr(db_or_connection, 'connection', db_or_connection)
        self.pool_catalog_table = 'pool_catalog_v2'
        self.account_codec = AccountCodec()
        self.current_swap_application_id = self._normalize_optional_application_id(current_swap_application_id)

    def _connection(self):
        if self.db is not None:
            self.db.ensure_fresh_read_connection()
            self.connection = self.db.connection
        return self.connection

    def _cursor(self, **kwargs):
        return self._connection().cursor(**kwargs)

    def _normalize_optional_application_id(self, application_id: object) -> str | None:
        if application_id in (None, ''):
            return None
        value = str(application_id).strip()
        if not value:
            return None
        if value.startswith('0x') or value.startswith('0X'):
            trimmed = value[2:]
            if trimmed:
                return trimmed
        return value

    def ensure_schema(self) -> None:
        cursor = self._cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.pool_catalog_table} (
                    pool_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    pool_application VARCHAR(256) NOT NULL,
                    pool_application_id VARCHAR(256) NOT NULL,
                    pool_chain_id VARCHAR(64) NULL,
                    token_0 VARCHAR(256) NOT NULL,
                    token_1 VARCHAR(256) NOT NULL,
                    creator_account VARCHAR(256) NULL,
                    event_family VARCHAR(64) NOT NULL,
                    source_event_key VARCHAR(255) NOT NULL,
                    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    PRIMARY KEY (pool_id),
                    UNIQUE KEY uq_pool_catalog_v2_application (pool_application),
                    KEY idx_pool_catalog_v2_application_id (pool_application_id)
                )
                '''
            )
            self._migrate_pool_application_id_column(cursor)
            self._migrate_pool_application_account_format(cursor)
            self._migrate_creator_account_column(cursor)
            self._connection().commit()
        finally:
            cursor.close()

    def _migrate_pool_application_id_column(self, cursor) -> None:
        cursor.execute(f"SHOW COLUMNS FROM {self.pool_catalog_table} LIKE 'pool_application_id'")
        row = cursor.fetchone()
        if row is None:
            return
        column_type = str(row.get('Type') if isinstance(row, dict) else row[1]).lower()
        if 'varchar(256)' in column_type:
            return
        cursor.execute(
            f'''
            ALTER TABLE {self.pool_catalog_table}
            MODIFY COLUMN pool_application_id VARCHAR(256) NOT NULL
            '''
        )

    def _migrate_creator_account_column(self, cursor) -> None:
        cursor.execute(f"SHOW COLUMNS FROM {self.pool_catalog_table} LIKE 'creator_account'")
        if cursor.fetchone() is not None:
            return
        cursor.execute(
            f'''
            ALTER TABLE {self.pool_catalog_table}
            ADD COLUMN creator_account VARCHAR(256) NULL AFTER token_1
            '''
        )

    def _migrate_pool_application_account_format(self, cursor) -> None:
        # Legacy one-time migration for pre-canonical rows. Runtime writes must
        # already use AccountCodec public-account format.
        cursor.execute(
            f'''
            UPDATE {self.pool_catalog_table}
            SET pool_application = CONCAT('0x', pool_application_id, '@', pool_chain_id)
            WHERE pool_chain_id IS NOT NULL
              AND pool_chain_id != ''
              AND pool_application_id NOT LIKE '0x%'
              AND CHAR_LENGTH(pool_application_id) IN (40, 64)
              AND pool_application_id REGEXP '^[0-9A-Fa-f]+$'
              AND pool_application != CONCAT('0x', pool_application_id, '@', pool_chain_id)
            '''
        )

    def materialize_events(self, events: list[dict[str, object]]) -> int:
        rows = [
            row
            for row in (self._catalog_row_from_event(event) for event in events)
            if row is not None
        ]
        if not rows:
            return 0
        cursor = self._cursor()
        try:
            for row in rows:
                cursor.execute(
                    f'''
                    INSERT INTO {self.pool_catalog_table} (
                        pool_application,
                        pool_application_id,
                        pool_chain_id,
                        token_0,
                        token_1,
                        creator_account,
                        event_family,
                        source_event_key
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pool_application_id = VALUES(pool_application_id),
                        pool_chain_id = VALUES(pool_chain_id),
                        token_0 = VALUES(token_0),
                        token_1 = VALUES(token_1),
                        creator_account = VALUES(creator_account),
                        event_family = VALUES(event_family),
                        source_event_key = VALUES(source_event_key)
                    ''',
                    (
                        row['pool_application'],
                        row['pool_application_id'],
                        row.get('pool_chain_id'),
                        row['token_0'],
                        row['token_1'],
                        row.get('creator_account'),
                        row['event_family'],
                        row['source_event_key'],
                    ),
                )
            self._connection().commit()
            return len(rows)
        finally:
            cursor.close()

    def list_pool_catalog(self) -> list[dict]:
        cursor = self._cursor(dictionary=True)
        try:
            current_swap_filter = ''
            params = ()
            if self.current_swap_application_id is not None:
                current_swap_filter = 'WHERE pool_app.parent_application_id = %s'
                params = (self.current_swap_application_id,)
            cursor.execute(
                f'''
                SELECT
                    pc.pool_id,
                    pc.pool_application,
                    pc.token_0,
                    pc.token_1,
                    pc.creator_account
                FROM {self.pool_catalog_table} pc
                LEFT JOIN application_registry pool_app
                  ON pool_app.application_id = pc.pool_application_id
                 AND pool_app.app_type = 'pool'
                {current_swap_filter}
                ORDER BY pc.pool_id ASC
                ''',
                params,
            )
            return [
                {
                    'pool_id': int(row['pool_id']),
                    'pool_application': row['pool_application'],
                    'token_0': row['token_0'],
                    'token_1': row['token_1'],
                    'creator_account': row.get('creator_account'),
                }
                for row in (cursor.fetchall() or [])
            ]
        finally:
            cursor.close()

    def _catalog_row_from_event(self, event: dict[str, object]) -> dict[str, object] | None:
        if event.get('normalization_status') != 'observed':
            return None
        event_family = event.get('event_family')
        if event_family not in self.POOL_CREATED_FAMILIES:
            return None
        payload = self._payload_dict(event.get('event_payload_json'))
        decoded_payload = self._payload_dict(payload.get('decoded_payload_json'))
        pool_application = self._account_to_pool_application(decoded_payload.get('pool_application'))
        if pool_application is None:
            return None
        token_0 = decoded_payload.get('token_0')
        if token_0 in (None, ''):
            return None
        token_1 = decoded_payload.get('token_1')
        if token_1 in (None, ''):
            token_1 = 'TLINERA'
        creator_account = self._account_to_user_account(decoded_payload.get('creator'))
        parsed_pool_application = self.account_codec.parse_account(pool_application)
        return {
            'pool_application': pool_application,
            'pool_application_id': self.account_codec.application_id_from_account(pool_application),
            'pool_chain_id': parsed_pool_application['chain_id'],
            'token_0': str(token_0),
            'token_1': str(token_1),
            'creator_account': creator_account,
            'event_family': str(event_family),
            'source_event_key': str(event.get('normalized_event_id') or event.get('source_event_key')),
        }

    def _payload_dict(self, payload: object) -> dict[str, object]:
        if isinstance(payload, str):
            return json.loads(payload)
        if isinstance(payload, dict):
            return payload
        return {}

    def _account_to_pool_application(self, account: object) -> str | None:
        public_account = self.account_codec.public_account_from_payload(account)
        if public_account is None:
            return None
        parsed = self.account_codec.parse_account(public_account)
        if parsed['owner'] == self.account_codec.CHAIN_OWNER:
            return None
        return self.account_codec.format_account(
            chain_id=parsed['chain_id'],
            owner=parsed['owner'],
        )


    def _account_to_user_account(self, account: object) -> str | None:
        public_account = self.account_codec.public_account_from_payload(account)
        if public_account is None:
            return None
        parsed = self.account_codec.parse_account(public_account)
        if parsed['owner'] == self.account_codec.CHAIN_OWNER:
            return None
        return self.account_codec.format_account(
            chain_id=parsed['chain_id'],
            owner=parsed['owner'],
        )
