class PositionMetricsPoolStateSnapshot:
    def __init__(self, payload: dict | None):
        self.payload = payload

    def raw(self) -> dict | None:
        return self.payload

    def fee_free_reserve_0(self):
        if self.payload is None:
            return None
        return self.payload.get('fee_free_reserve_0')

    def current_reserve_0(self):
        if self.payload is None:
            return None
        return self.payload.get('current_reserve_0')

    def fee_free_reserve_1(self):
        if self.payload is None:
            return None
        return self.payload.get('fee_free_reserve_1')

    def current_reserve_1(self):
        if self.payload is None:
            return None
        return self.payload.get('current_reserve_1')

    def current_total_supply(self):
        if self.payload is None:
            return None
        return self.payload.get('current_total_supply')

    def fee_free_total_supply(self):
        if self.payload is None:
            return None
        return self.payload.get('fee_free_total_supply')

    def last_transaction_id(self):
        if self.payload is None:
            return None
        return self.payload.get('last_transaction_id')

    def last_trade_time_ms(self):
        if self.payload is None:
            return None
        return self.payload.get('last_trade_time_ms')

    def last_liquidity_event_time_ms(self):
        if self.payload is None:
            return None
        return self.payload.get('last_liquidity_event_time_ms')

    def fee_free_basis_transaction_id(self):
        if self.payload is None:
            return None
        return self.payload.get('fee_free_basis_transaction_id')

    def fee_free_basis_time_ms(self):
        if self.payload is None:
            return None
        return self.payload.get('fee_free_basis_time_ms')

    def virtual_initial_liquidity(self) -> bool:
        if self.payload is None:
            return False
        return bool((self.payload.get('state_payload_json') or {}).get('virtual_initial_liquidity'))

    def fee_to_account_latest_known(self) -> str | None:
        if self.payload is None:
            return None
        value = (self.payload.get('state_payload_json') or {}).get('fee_to_account_latest_known')
        if value in (None, ''):
            return None
        return str(value)

    def pool_created_metadata(self) -> dict | None:
        if self.payload is None:
            return None
        metadata = (self.payload.get('state_payload_json') or {}).get('pool_created_metadata')
        if not isinstance(metadata, dict):
            return None
        return dict(metadata)

    def summary_dict(self) -> dict | None:
        if self.payload is None:
            return None
        return {
            'last_transaction_id': self._int_or_none(self.last_transaction_id()),
            'last_trade_time_ms': self._int_or_none(self.last_trade_time_ms()),
            'last_liquidity_event_time_ms': self._int_or_none(self.last_liquidity_event_time_ms()),
        }

    def shadow_latest_dict(self) -> dict:
        return {
            'latest_pool_transaction_id': self._int_or_none(self.last_transaction_id()),
            'latest_pool_trade_time_ms': self._int_or_none(self.last_trade_time_ms()),
            'latest_pool_liquidity_event_time_ms': self._int_or_none(self.last_liquidity_event_time_ms()),
        }

    def _int_or_none(self, value: object) -> int | None:
        if value in (None, ''):
            return None
        return int(value)
