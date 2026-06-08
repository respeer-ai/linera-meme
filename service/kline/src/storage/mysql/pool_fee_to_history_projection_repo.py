import json

from account_codec import AccountCodec


class PoolFeeToHistoryProjectionRepository:
    POOL_CREATED_FAMILIES = {
        'swap_pool_created_recorded',
        'swap_user_pool_created_recorded',
    }
    SET_FEE_TO_FAMILY = 'pool_set_fee_to_message_observed'

    def __init__(self, db_or_connection):
        self.db = db_or_connection if hasattr(db_or_connection, 'ensure_fresh_read_connection') else None
        self.connection = getattr(db_or_connection, 'connection', db_or_connection)
        self.table = 'pool_fee_to_history_v2'
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
                CREATE TABLE IF NOT EXISTS {self.table} (
                    pool_fee_to_history_id VARCHAR(512) NOT NULL,
                    pool_application VARCHAR(256) NOT NULL,
                    pool_application_id VARCHAR(256) NOT NULL,
                    pool_chain_id VARCHAR(64) NULL,
                    transaction_id BIGINT NULL,
                    event_time_ms BIGINT NULL,
                    fee_to_account VARCHAR(256) NOT NULL,
                    event_family VARCHAR(64) NOT NULL,
                    source_event_key VARCHAR(255) NOT NULL,
                    indexed_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
                    updated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
                    PRIMARY KEY (pool_fee_to_history_id),
                    KEY idx_pool_fee_to_history_pool_time (pool_application, event_time_ms, transaction_id),
                    KEY idx_pool_fee_to_history_application_id (pool_application_id)
                )
                '''
            )
            self._migrate_widths(cursor)
            self._connection().commit()
        finally:
            cursor.close()

    def _migrate_widths(self, cursor) -> None:
        expected_widths = {
            'pool_fee_to_history_id': 'varchar(512)',
            'pool_application': 'varchar(256)',
            'pool_application_id': 'varchar(256)',
            'source_event_key': 'varchar(255)',
        }
        for column_name, expected_type in expected_widths.items():
            cursor.execute(f"SHOW COLUMNS FROM {self.table} LIKE %s", (column_name,))
            row = cursor.fetchone()
            if row is None:
                return
            column_type = str(row.get('Type') if isinstance(row, dict) else row[1]).lower()
            if expected_type not in column_type:
                break
        else:
            return
        cursor.execute(
            f'''
            ALTER TABLE {self.table}
            MODIFY COLUMN pool_fee_to_history_id VARCHAR(512) NOT NULL,
            MODIFY COLUMN pool_application VARCHAR(256) NOT NULL,
            MODIFY COLUMN pool_application_id VARCHAR(256) NOT NULL,
            MODIFY COLUMN source_event_key VARCHAR(255) NOT NULL
            '''
        )

    def materialize_events(self, events: list[dict[str, object]]) -> int:
        rows = [
            row
            for row in (self._history_row_from_event(event) for event in events)
            if row is not None
        ]
        if not rows:
            return 0
        cursor = self._cursor()
        try:
            for row in rows:
                cursor.execute(
                    f'''
                    INSERT INTO {self.table} (
                        pool_fee_to_history_id,
                        pool_application,
                        pool_application_id,
                        pool_chain_id,
                        transaction_id,
                        event_time_ms,
                        fee_to_account,
                        event_family,
                        source_event_key
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        pool_application = VALUES(pool_application),
                        pool_application_id = VALUES(pool_application_id),
                        pool_chain_id = VALUES(pool_chain_id),
                        transaction_id = VALUES(transaction_id),
                        event_time_ms = VALUES(event_time_ms),
                        fee_to_account = VALUES(fee_to_account),
                        event_family = VALUES(event_family),
                        source_event_key = VALUES(source_event_key)
                    ''',
                    (
                        row['pool_fee_to_history_id'],
                        row['pool_application'],
                        row['pool_application_id'],
                        row.get('pool_chain_id'),
                        row.get('transaction_id'),
                        row.get('event_time_ms'),
                        row['fee_to_account'],
                        row['event_family'],
                        row['source_event_key'],
                    ),
                )
            self._connection().commit()
            return len(rows)
        finally:
            cursor.close()

    def list_pool_fee_to_history(self, *, pool_application_id: str) -> list[dict[str, object]]:
        cursor = self._cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT
                    transaction_id,
                    event_time_ms,
                    fee_to_account,
                    event_family,
                    source_event_key
                FROM {self.table}
                WHERE pool_application = %s
                ORDER BY event_time_ms ASC, transaction_id ASC, pool_fee_to_history_id ASC
                ''',
                (pool_application_id,),
            )
            return [
                {
                    'transaction_id': row.get('transaction_id'),
                    'created_at': row.get('event_time_ms'),
                    'fee_to_account': row.get('fee_to_account'),
                    'event_family': row.get('event_family'),
                    'source_event_key': row.get('source_event_key'),
                }
                for row in (cursor.fetchall() or [])
            ]
        finally:
            cursor.close()

    def _history_row_from_event(self, event: dict[str, object]) -> dict[str, object] | None:
        if event.get('normalization_status') != 'observed':
            return None
        event_family = event.get('event_family')
        payload = self._payload_dict(event.get('event_payload_json'))
        decoded_payload = self._payload_dict(payload.get('decoded_payload_json'))
        if event_family in self.POOL_CREATED_FAMILIES:
            return self._pool_created_history_row(event, decoded_payload)
        if event_family == self.SET_FEE_TO_FAMILY:
            return self._set_fee_to_history_row(event, decoded_payload)
        return None

    def _pool_created_history_row(self, event: dict[str, object], decoded_payload: dict[str, object]) -> dict[str, object] | None:
        pool_application = self._pool_application_from_payload(decoded_payload.get('pool_application'))
        fee_to_account = self._user_account_from_payload(decoded_payload.get('creator'))
        if pool_application is None or fee_to_account is None:
            return None
        parsed_pool_application = self.account_codec.parse_account(pool_application)
        source_event_key = str(event.get('normalized_event_id') or event.get('source_event_key'))
        return {
            'pool_fee_to_history_id': f'{pool_application}:0:0:pool_create_default_fee_to:{source_event_key}',
            'pool_application': pool_application,
            'pool_application_id': self.account_codec.application_id_from_account(pool_application),
            'pool_chain_id': parsed_pool_application['chain_id'],
            'transaction_id': 0,
            'event_time_ms': 0,
            'fee_to_account': fee_to_account,
            'event_family': str(event.get('event_family')),
            'source_event_key': source_event_key,
        }

    def _set_fee_to_history_row(self, event: dict[str, object], decoded_payload: dict[str, object]) -> dict[str, object] | None:
        pool_application = self._pool_application_from_event(event)
        fee_to_account = self._extract_fee_to_account(decoded_payload)
        if pool_application is None or fee_to_account is None:
            return None
        parsed_pool_application = self.account_codec.parse_account(pool_application)
        transaction_id = self._search_first(decoded_payload, {'transaction_id'})
        created_at = self._event_time_to_millis(self._search_first_entry(decoded_payload, {'created_at_micros', 'created_at'}))
        source_event_key = str(event.get('normalized_event_id') or event.get('source_event_key'))
        return {
            'pool_fee_to_history_id': f'{pool_application}:{created_at or 0}:{transaction_id or 0}:set_fee_to:{source_event_key}',
            'pool_application': pool_application,
            'pool_application_id': self.account_codec.application_id_from_account(pool_application),
            'pool_chain_id': parsed_pool_application['chain_id'],
            'transaction_id': int(transaction_id) if transaction_id not in (None, '') else None,
            'event_time_ms': created_at,
            'fee_to_account': fee_to_account,
            'event_family': str(event.get('event_family')),
            'source_event_key': source_event_key,
        }

    def _pool_application_from_event(self, event: dict[str, object]) -> str | None:
        value = event.get('application_id')
        if value in (None, ''):
            return None
        account = str(value)
        if '@' in account:
            return account
        chain_id = event.get('source_chain_id') or event.get('target_chain_id')
        if chain_id in (None, ''):
            return None
        if not account.startswith('0x'):
            account = f'0x{account}'
        return self.account_codec.format_account(chain_id=str(chain_id), owner=account)

    def _pool_application_from_payload(self, value: object) -> str | None:
        public_account = self.account_codec.public_account_from_payload(value)
        if public_account is None:
            return None
        parsed = self.account_codec.parse_account(public_account)
        if parsed['owner'] == self.account_codec.CHAIN_OWNER:
            return None
        return self.account_codec.format_account(chain_id=parsed['chain_id'], owner=parsed['owner'])

    def _user_account_from_payload(self, value: object) -> str | None:
        public_account = self.account_codec.public_account_from_payload(value)
        if public_account is None:
            return None
        parsed = self.account_codec.parse_account(public_account)
        if parsed['owner'] == self.account_codec.CHAIN_OWNER:
            return None
        return self.account_codec.format_account(chain_id=parsed['chain_id'], owner=parsed['owner'])

    def _extract_fee_to_account(self, payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None
        for key in ('fee_to', 'feeTo', 'new_fee_to', 'newFeeTo', 'account', 'owner'):
            account = self._user_account_from_payload(payload.get(key))
            if account is not None:
                return account
        for value in payload.values():
            account = self._extract_fee_to_account(value)
            if account is not None:
                return account
        return None

    def _payload_dict(self, payload: object) -> dict[str, object]:
        if isinstance(payload, str):
            return json.loads(payload)
        if isinstance(payload, dict):
            return payload
        return {}

    def _search_first(self, payload: object, keys: set[str]) -> object:
        entry = self._search_first_entry(payload, keys)
        if entry is None:
            return None
        return entry[1]

    def _search_first_entry(self, payload: object, keys: set[str]) -> tuple[str, object] | None:
        if not isinstance(payload, dict):
            return None
        for key, value in payload.items():
            if key in keys and value not in (None, ''):
                return (key, value)
            nested = self._search_first_entry(value, keys)
            if nested is not None:
                return nested
        return None

    def _event_time_to_millis(self, entry: tuple[str, object] | None) -> int | None:
        if entry is None:
            return None
        key, value = entry
        if value in (None, ''):
            return None
        integer = int(value)
        if key == 'created_at_micros':
            return integer // 1000
        return integer
