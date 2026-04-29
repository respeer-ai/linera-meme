import json


class PositionMetricsSnapshotSourceRepository:
    def __init__(self, connection, *, pools_table: str = 'pools'):
        self.connection = connection
        self.pools_table = pools_table
        self.normalized_events_table = 'normalized_events'

    def list_pool_trade_history(
        self,
        *,
        pool_application_id: str,
    ) -> list[dict[str, object]]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT
                    st.transaction_id,
                    st.trade_time_ms,
                    st.side,
                    st.event_payload_json
                FROM settled_trades st
                JOIN {self.pools_table} p
                  ON p.pool_application = CONCAT(st.pool_chain_id, ':', st.pool_application_id)
                WHERE p.pool_application = %s
                ORDER BY st.trade_time_ms ASC, st.transaction_index ASC, st.settled_trade_id ASC
                ''',
                (pool_application_id,),
            )
            rows = cursor.fetchall() or []
            return [self._build_trade_history_row(dict(row)) for row in rows]
        finally:
            cursor.close()

    def list_pool_liquidity_history(
        self,
        *,
        pool_application_id: str,
    ) -> list[dict[str, object]]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT
                    slc.owner,
                    slc.transaction_id,
                    slc.change_type,
                    slc.liquidity_delta,
                    slc.amount_0_delta,
                    slc.amount_1_delta,
                    slc.event_time_ms
                FROM settled_liquidity_changes slc
                JOIN {self.pools_table} p
                  ON p.pool_application = CONCAT(slc.pool_chain_id, ':', slc.pool_application_id)
                WHERE p.pool_application = %s
                ORDER BY slc.event_time_ms ASC, slc.transaction_index ASC, slc.settled_liquidity_change_id ASC
                ''',
                (pool_application_id,),
            )
            rows = cursor.fetchall() or []
            return [self._build_liquidity_history_row(dict(row)) for row in rows]
        finally:
            cursor.close()

    def list_position_liquidity_history(
        self,
        *,
        owner: str,
        pool_application_id: str,
    ) -> list[dict[str, object]]:
        cursor = self.connection.cursor(dictionary=True)
        try:
            cursor.execute(
                f'''
                SELECT
                    slc.owner,
                    slc.transaction_id,
                    slc.change_type,
                    slc.liquidity_delta,
                    slc.amount_0_delta,
                    slc.amount_1_delta,
                    slc.event_time_ms
                FROM settled_liquidity_changes slc
                JOIN {self.pools_table} p
                  ON p.pool_application = CONCAT(slc.pool_chain_id, ':', slc.pool_application_id)
                WHERE p.pool_application = %s
                  AND slc.owner = %s
                ORDER BY slc.event_time_ms ASC, slc.transaction_index ASC, slc.settled_liquidity_change_id ASC
                ''',
                (pool_application_id, self._to_settled_owner(owner)),
            )
            rows = cursor.fetchall() or []
            return [self._build_liquidity_history_row(dict(row)) for row in rows]
        finally:
            cursor.close()

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

    def _build_trade_history_row(self, row: dict[str, object]) -> dict[str, object]:
        payload = row.get('event_payload_json')
        if isinstance(payload, str):
            payload = json.loads(payload)
        transaction = (payload or {}).get('transaction') or {}
        side = str(row.get('side') or '')
        return {
            'transaction_id': int(row['transaction_id']) if row.get('transaction_id') is not None else None,
            'transaction_type': 'BuyToken0' if side == 'buy_token_0' else 'SellToken0',
            'amount_0_in': self._string_or_none(transaction.get('amount_0_in')),
            'amount_0_out': self._string_or_none(transaction.get('amount_0_out')),
            'amount_1_in': self._string_or_none(transaction.get('amount_1_in')),
            'amount_1_out': self._string_or_none(transaction.get('amount_1_out')),
            'liquidity': self._string_or_none(transaction.get('liquidity')),
            'created_at': int(row['trade_time_ms']) if row.get('trade_time_ms') is not None else None,
            'from_account': self._account_payload_to_string(transaction.get('from')),
        }

    def _build_liquidity_history_row(self, row: dict[str, object]) -> dict[str, object]:
        change_type = str(row.get('change_type') or '')
        is_add = change_type == 'add_liquidity'
        amount_0_delta = self._string_or_none(row.get('amount_0_delta'))
        amount_1_delta = self._string_or_none(row.get('amount_1_delta'))
        liquidity_delta = self._string_or_none(row.get('liquidity_delta'))
        return {
            'transaction_id': int(row['transaction_id']) if row.get('transaction_id') is not None else None,
            'transaction_type': 'AddLiquidity' if is_add else 'RemoveLiquidity',
            'amount_0_in': amount_0_delta if is_add else None,
            'amount_0_out': None if is_add else amount_0_delta,
            'amount_1_in': amount_1_delta if is_add else None,
            'amount_1_out': None if is_add else amount_1_delta,
            'liquidity': liquidity_delta,
            'created_at': int(row['event_time_ms']) if row.get('event_time_ms') is not None else None,
            'from_account': self._from_account(row.get('owner')),
        }

    def _build_fee_to_history_row(self, row: dict[str, object]) -> dict[str, object] | None:
        payload = row.get('event_payload_json')
        if isinstance(payload, str):
            payload = json.loads(payload)
        decoded_payload = (payload or {}).get('decoded_payload_json') or {}
        fee_to_account = self._extract_fee_to_account(decoded_payload)
        created_at_micros = self._search_first(decoded_payload, {'created_at_micros', 'created_at'})
        transaction_id = self._search_first(decoded_payload, {'transaction_id'})
        if created_at_micros is None and transaction_id is None and fee_to_account is None:
            return None
        return {
            'transaction_id': int(transaction_id) if transaction_id not in (None, '') else None,
            'created_at': self._to_millis(created_at_micros),
            'fee_to_account': fee_to_account,
            'source_chain_id': row.get('source_chain_id'),
            'target_chain_id': row.get('target_chain_id'),
            'source_cert_hash': row.get('source_cert_hash'),
            'transaction_index': row.get('transaction_index'),
            'message_index': row.get('message_index'),
            'decoded_payload_json': decoded_payload,
        }

    def _string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def _account_payload_to_string(self, account: object) -> str | None:
        if not isinstance(account, dict):
            return None
        chain_id = account.get('chain_id')
        owner = account.get('owner')
        if chain_id is None or owner is None:
            return None
        return f'{chain_id}:{owner}'

    def _to_settled_owner(self, owner: str) -> str:
        chain_id, owner_id = owner.split(':', 1)
        return f'{owner_id}@{chain_id}'

    def _from_account(self, owner: object) -> str | None:
        if not isinstance(owner, str) or '@' not in owner:
            return None
        owner_id, chain_id = owner.split('@', 1)
        return f'{chain_id}:{owner_id}'

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
            account_string = self._account_payload_to_string(account)
            if account_string is not None:
                return account_string
        for value in payload.values():
            account_string = self._extract_fee_to_account(value)
            if account_string is not None:
                return account_string
        return None

    def _search_first(self, payload: object, keys: set[str]) -> object:
        if not isinstance(payload, dict):
            return None
        for key, value in payload.items():
            if key in keys and value not in (None, ''):
                return value
            nested = self._search_first(value, keys)
            if nested not in (None, ''):
                return nested
        return None

    def _to_millis(self, value: object) -> int | None:
        if value in (None, ''):
            return None
        integer = int(value)
        if integer > 10**12:
            return integer // 1000
        return integer
