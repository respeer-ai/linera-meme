import json
from account_codec import AccountCodec


class PoolCatalogProjectionRepository:
    POOL_CREATED_FAMILIES = {
        'swap_pool_created_recorded',
        'swap_user_pool_created_recorded',
    }

    def __init__(self, db_or_connection):
        self.db = db_or_connection if hasattr(db_or_connection, 'ensure_fresh_read_connection') else None
        self.connection = getattr(db_or_connection, 'connection', db_or_connection)
        self.pool_catalog_table = 'pool_catalog_v2'
        self.account_codec = AccountCodec()

    def _connection(self):
        if self.db is not None:
            self.db.ensure_fresh_read_connection()
            self.connection = self.db.connection
        return self.connection

    def _cursor(self, **kwargs):
        return self._connection().cursor(**kwargs)

    def ensure_schema(self) -> None:
        cursor = self._cursor()
        try:
            cursor.execute(
                f'''
                CREATE TABLE IF NOT EXISTS {self.pool_catalog_table} (
                    pool_id INT UNSIGNED NOT NULL AUTO_INCREMENT,
                    pool_application VARCHAR(256) NOT NULL,
                    pool_application_id VARCHAR(128) NOT NULL,
                    pool_chain_id VARCHAR(64) NULL,
                    token_0 VARCHAR(256) NOT NULL,
                    token_1 VARCHAR(256) NOT NULL,
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
            self._migrate_pool_application_account_format(cursor)
            self._connection().commit()
        finally:
            cursor.close()

    def _migrate_pool_application_account_format(self, cursor) -> None:
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
                        event_family,
                        source_event_key
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pool_application_id = VALUES(pool_application_id),
                        pool_chain_id = VALUES(pool_chain_id),
                        token_0 = VALUES(token_0),
                        token_1 = VALUES(token_1),
                        event_family = VALUES(event_family),
                        source_event_key = VALUES(source_event_key)
                    ''',
                    (
                        row['pool_application'],
                        row['pool_application_id'],
                        row.get('pool_chain_id'),
                        row['token_0'],
                        row['token_1'],
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
            cursor.execute(
                f'''
                SELECT
                    pool_id,
                    pool_application,
                    token_0,
                    token_1
                FROM {self.pool_catalog_table}
                ORDER BY pool_id ASC
                '''
            )
            return [
                {
                    'pool_id': int(row['pool_id']),
                    'pool_application': row['pool_application'],
                    'token_0': row['token_0'],
                    'token_1': row['token_1'],
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
        parsed_pool_application = self.account_codec.parse_account(pool_application)
        return {
            'pool_application': pool_application,
            'pool_application_id': self.account_codec.application_id_from_account(pool_application),
            'pool_chain_id': parsed_pool_application['chain_id'],
            'token_0': str(token_0),
            'token_1': str(token_1),
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
        if isinstance(account, str):
            try:
                parsed = self.account_codec.parse_account(account)
            except ValueError:
                return None
            if parsed['owner'] == self.account_codec.CHAIN_OWNER:
                return None
            return self.account_codec.format_account(
                chain_id=parsed['chain_id'],
                owner=parsed['owner'],
            )
        if not isinstance(account, dict):
            return None
        chain_id = account.get('chain_id')
        owner = account.get('owner')
        if chain_id in (None, '') or owner in (None, ''):
            return None
        owner_value = str(owner)
        if not owner_value.startswith('0x'):
            owner_value = f'0x{owner_value}'
        return self.account_codec.format_account(chain_id=chain_id, owner=owner_value)
