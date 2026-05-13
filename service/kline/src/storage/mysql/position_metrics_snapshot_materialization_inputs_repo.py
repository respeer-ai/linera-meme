import json

from account_codec import AccountCodec
from storage.mysql.settled_pool_history_projection_repo import SettledPoolHistoryProjectionRepository
from storage.mysql.settled_liquidity_projection_repo import SettledLiquidityProjectionRepository
from storage.mysql.settled_product_transaction_adapter import SettledProductTransactionAdapter
from storage.mysql.settled_trade_projection_repo import SettledTradeProjectionRepository


class PositionMetricsSnapshotMaterializationInputsRepository:
    def __init__(
        self,
        connection,
        *,
        pools_table: str = 'pools',
        transaction_adapter=None,
        settled_trade_projection_repo=None,
        settled_liquidity_projection_repo=None,
        settled_pool_history_projection_repo=None,
    ):
        self.connection = connection
        self.pools_table = pools_table
        self.normalized_events_table = 'normalized_events'
        self.cursor_dict = None
        self.account_codec = AccountCodec()
        self.transaction_adapter = transaction_adapter or SettledProductTransactionAdapter()
        self.settled_trade_projection_repo = (
            settled_trade_projection_repo
            or SettledTradeProjectionRepository(
                self,
                transaction_adapter=self.transaction_adapter,
            )
        )
        self.settled_liquidity_projection_repo = (
            settled_liquidity_projection_repo
            or SettledLiquidityProjectionRepository(
                self,
                transaction_adapter=self.transaction_adapter,
            )
        )
        self.settled_pool_history_projection_repo = (
            settled_pool_history_projection_repo
            or SettledPoolHistoryProjectionRepository(
                settled_trade_projection_repo=self.settled_trade_projection_repo,
                settled_liquidity_projection_repo=self.settled_liquidity_projection_repo,
            )
        )

    def ensure_fresh_read_connection(self):
        if self.cursor_dict is not None:
            try:
                self.cursor_dict.close()
            except Exception:
                pass
        self.cursor_dict = self.connection.cursor(dictionary=True)

    def list_pool_transaction_history(
        self,
        *,
        pool_application_id: str,
        pool_chain_id: str | None = None,
    ) -> list[dict[str, object]]:
        self.account_codec.parse_account(pool_application_id)
        history = self.settled_pool_history_projection_repo.get_pool_transaction_history(
            pool_application=pool_application_id,
            pool_id=None,
        )
        return [] if history is None else list(history)

    def list_position_liquidity_history(
        self,
        *,
        owner: str,
        pool_application_id: str,
    ) -> list[dict[str, object]]:
        history = self.settled_liquidity_projection_repo.get_position_liquidity_history(
            owner=owner,
            pool_application=pool_application_id,
            pool_id=None,
        )
        return [] if history is None else list(history)

    def list_pool_fee_to_history(
        self,
        *,
        pool_application_id: str,
    ) -> list[dict[str, object]]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT
                    event_payload_json,
                    source_chain_id,
                    target_chain_id,
                    source_cert_hash,
                    transaction_index,
                    message_index
                FROM {self.normalized_events_table}
                WHERE application_id = %s
                  AND event_family = %s
                  AND normalization_status = %s
                ORDER BY source_cert_hash ASC, transaction_index ASC, message_index ASC, normalized_event_id ASC
                ''',
                (
                    pool_application_id,
                    'pool_set_fee_to_message_observed',
                    'observed',
                ),
            )
            rows = cursor.fetchall() or []
            return [
                row_dict
                for row_dict in (
                    self._build_fee_to_history_row(dict(row))
                    for row in rows
                )
                if row_dict is not None
            ]
        finally:
            cursor.close()

    def get_pool_created_metadata(
        self,
        *,
        pool_application_id: str,
    ) -> dict[str, object] | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT
                    event_family,
                    event_payload_json,
                    source_chain_id,
                    target_chain_id,
                    source_cert_hash,
                    transaction_index,
                    message_index
                FROM {self.normalized_events_table}
                WHERE application_id = %s
                  AND event_family IN (%s, %s)
                  AND normalization_status = %s
                ORDER BY source_cert_hash ASC, transaction_index ASC, message_index ASC, normalized_event_id ASC
                LIMIT 1
                ''',
                (
                    pool_application_id,
                    'swap_pool_created_recorded',
                    'swap_user_pool_created_recorded',
                    'observed',
                ),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._build_pool_created_metadata(dict(row))
        finally:
            cursor.close()

    def _build_fee_to_history_row(self, row: dict[str, object]) -> dict[str, object] | None:
        payload = row.get('event_payload_json')
        if isinstance(payload, str):
            payload = json.loads(payload)
        decoded_payload = (payload or {}).get('decoded_payload_json') or {}
        fee_to_account = self._extract_fee_to_account(decoded_payload)
        created_at_entry = self._search_first_entry(decoded_payload, {'created_at_micros', 'created_at'})
        transaction_id = self._search_first(decoded_payload, {'transaction_id'})
        if created_at_entry is None and transaction_id is None and fee_to_account is None:
            return None
        return {
            'transaction_id': int(transaction_id) if transaction_id not in (None, '') else None,
            'created_at': self._event_time_to_millis(created_at_entry),
            'fee_to_account': fee_to_account,
            'source_chain_id': row.get('source_chain_id'),
            'target_chain_id': row.get('target_chain_id'),
            'source_cert_hash': row.get('source_cert_hash'),
            'transaction_index': row.get('transaction_index'),
            'message_index': row.get('message_index'),
            'decoded_payload_json': decoded_payload,
        }

    def _build_pool_created_metadata(self, row: dict[str, object]) -> dict[str, object] | None:
        payload = row.get('event_payload_json')
        if isinstance(payload, str):
            payload = json.loads(payload)
        decoded_payload = (payload or {}).get('decoded_payload_json') or {}
        token_0 = decoded_payload.get('token_0')
        token_1 = decoded_payload.get('token_1')
        if token_0 in (None, ''):
            return None
        if token_1 in (None, ''):
            token_1 = 'TLINERA'
        pool_application = decoded_payload.get('pool_application')
        return {
            'event_family': row.get('event_family'),
            'pool_application': str(pool_application) if pool_application not in (None, '') else pool_application,
            'token_0': str(token_0),
            'token_1': str(token_1),
            'source_chain_id': row.get('source_chain_id'),
            'target_chain_id': row.get('target_chain_id'),
            'source_cert_hash': row.get('source_cert_hash'),
            'transaction_index': row.get('transaction_index'),
            'message_index': row.get('message_index'),
            'decoded_payload_json': decoded_payload,
        }

    def _extract_fee_to_account(self, payload: object) -> str | None:
        if not isinstance(payload, dict):
            return None
        for key in (
            'fee_to',
            'feeTo',
            'new_fee_to',
            'newFeeTo',
            'account',
            'owner',
        ):
            account = payload.get(key)
            account_string = self._account_like_to_public_string(account)
            if account_string is not None:
                return account_string
        for value in payload.values():
            account_string = self._extract_fee_to_account(value)
            if account_string is not None:
                return account_string
        return None

    def _account_like_to_public_string(self, account: object) -> str | None:
        account_string = self.transaction_adapter.account_payload_to_string(account)
        if account_string is not None:
            return account_string
        if isinstance(account, str):
            settled_owner = self.transaction_adapter.public_owner_from_settled_owner(account)
            if settled_owner is not None:
                return settled_owner
        return None

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
