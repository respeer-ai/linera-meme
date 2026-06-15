import json

from account_codec import AccountCodec


class PoolRegistryMetadataRepository:
    NATIVE_TOKEN_SENTINEL = 'TLINERA'

    def __init__(self, db_or_connection):
        self.db = db_or_connection if hasattr(db_or_connection, 'ensure_fresh_read_connection') else None
        self.connection = getattr(db_or_connection, 'connection', db_or_connection)
        self.account_codec = AccountCodec()

    def list_pool_metadata(self) -> list[dict]:
        cursor = self._cursor(dictionary=True)
        try:
            cursor.execute(
                '''
                SELECT
                    application_id,
                    chain_id,
                    metadata_json
                FROM application_registry
                WHERE app_type = 'pool'
                  AND status = 'active'
                  AND metadata_json IS NOT NULL
                '''
            )
            return [
                metadata
                for metadata in (self._metadata_from_row(row) for row in (cursor.fetchall() or []))
                if metadata is not None
            ]
        except Exception:
            return []
        finally:
            cursor.close()

    def _cursor(self, **kwargs):
        if self.db is not None:
            self.db.ensure_fresh_read_connection()
            self.connection = self.db.connection
        return self.connection.cursor(**kwargs)

    def _metadata_from_row(self, row: dict) -> dict | None:
        metadata = self._payload_dict(row.get('metadata_json'))
        pool_id = metadata.get('pool_id')
        token_0 = metadata.get('token_0')
        if pool_id in (None, '') or token_0 in (None, ''):
            return None
        application_id = row.get('application_id')
        chain_id = row.get('chain_id')
        if application_id in (None, '') or chain_id in (None, ''):
            return None
        pool_application = self.account_codec.format_account(
            chain_id=str(chain_id),
            owner=self._application_owner(application_id),
        )
        return {
            'pool_id': int(pool_id),
            'pool_application': pool_application,
            'pool_application_id': str(application_id),
            'pool_chain_id': str(chain_id),
            'token_0': str(token_0),
            'token_1': self._token_1(metadata.get('token_1')),
            'creator_account': metadata.get('creator_account'),
            'source': 'application_registry',
        }

    def _payload_dict(self, payload: object) -> dict[str, object]:
        if isinstance(payload, str):
            return json.loads(payload)
        if isinstance(payload, dict):
            return payload
        return {}

    def _application_owner(self, application_id: object) -> str:
        value = str(application_id)
        if value.startswith('0x'):
            return self.account_codec.format_owner(value)
        return self.account_codec.format_owner(f'0x{value}')

    def _token_1(self, value: object) -> str:
        if value in (None, ''):
            return self.NATIVE_TOKEN_SENTINEL
        return str(value)
