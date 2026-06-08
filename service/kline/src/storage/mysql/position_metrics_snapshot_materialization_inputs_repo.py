import json

from account_codec import AccountCodec
from storage.mysql.settled_pool_history_projection_repo import SettledPoolHistoryProjectionRepository
from storage.mysql.settled_liquidity_projection_repo import SettledLiquidityProjectionRepository
from storage.mysql.pool_fee_to_history_projection_repo import PoolFeeToHistoryProjectionRepository
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
        pool_fee_to_history_projection_repository=None,
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
        self.pool_fee_to_history_projection_repository = (
            pool_fee_to_history_projection_repository
            or PoolFeeToHistoryProjectionRepository(self)
        )

    def ensure_fresh_read_connection(self):
        if self.cursor_dict is not None:
            try:
                self.cursor_dict.close()
            except Exception:
                pass
        self.cursor_dict = self.connection.cursor(dictionary=True)

    def fresh_cursor(self, *, dictionary: bool = False):
        self.ensure_fresh_read_connection()
        return self.connection.cursor(dictionary=dictionary)

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

    def list_active_position_owners_for_pool(
        self,
        *,
        pool_application: str,
    ) -> list[str]:
        return self.settled_liquidity_projection_repo.list_active_position_owners_for_pool(
            pool_application=pool_application,
        )

    def list_pool_fee_to_history(
        self,
        *,
        pool_application_id: str,
    ) -> list[dict[str, object]]:
        return list(self.pool_fee_to_history_projection_repository.list_pool_fee_to_history(
            pool_application_id=pool_application_id,
        ) or [])

    def get_pool_created_metadata(
        self,
        *,
        pool_application_id: str,
    ) -> dict[str, object] | None:
        catalog_metadata = self._get_pool_created_metadata_from_catalog(
            pool_application_id=pool_application_id,
        )
        if catalog_metadata is not None:
            return catalog_metadata

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

    def _get_pool_created_metadata_from_catalog(
        self,
        *,
        pool_application_id: str,
    ) -> dict[str, object] | None:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                '''
                SELECT
                    pool_application,
                    token_0,
                    token_1,
                    creator_account,
                    event_family,
                    source_event_key
                FROM pool_catalog_v2
                WHERE pool_application = %s
                LIMIT 1
                ''',
                (pool_application_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            row = dict(row)
            token_0 = row.get('token_0')
            if token_0 in (None, ''):
                return None
            token_1 = row.get('token_1') or 'TLINERA'
            return {
                'event_family': row.get('event_family'),
                'pool_application': row.get('pool_application'),
                'token_0': str(token_0),
                'token_1': str(token_1),
                'creator_account': row.get('creator_account'),
                'source_event_key': row.get('source_event_key'),
                'source': 'pool_catalog_v2',
            }
        finally:
            cursor.close()

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
