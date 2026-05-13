class PoolExecutedEventPayload:
    TRADE_FAMILIES = {'pool_swap_executed'}
    LIQUIDITY_FAMILIES = {
        'pool_add_liquidity_executed',
        'pool_remove_liquidity_executed',
    }
    SUPPORTED_FAMILIES = TRADE_FAMILIES | LIQUIDITY_FAMILIES

    def __init__(self, *, event_family: str, execution: dict[str, object]):
        self.event_family = str(event_family)
        self.execution = dict(execution)

    @classmethod
    def from_event(cls, event: dict[str, object]):
        event_family = str(event.get('event_family') or '')
        if event_family not in cls.SUPPORTED_FAMILIES:
            return None
        payload = event.get('event_payload_json') or {}
        decoded_payload = payload.get('decoded_payload_json') or {}
        execution = decoded_payload.get('execution')
        if not isinstance(execution, dict):
            return None
        return cls(
            event_family=event_family,
            execution=execution,
        )

    def is_trade(self) -> bool:
        return self.event_family in self.TRADE_FAMILIES

    def is_liquidity(self) -> bool:
        return self.event_family in self.LIQUIDITY_FAMILIES

    def trade_type(self) -> str | None:
        value = self.execution.get('trade_type')
        if value is None:
            return None
        return str(value)

    def change_type(self) -> str | None:
        value = self.execution.get('change_type')
        if value is None:
            return None
        return str(value)

    def amount_0_in(self):
        return self.execution.get('amount_0_in')

    def amount_0_out(self):
        return self.execution.get('amount_0_out')

    def amount_1_in(self):
        return self.execution.get('amount_1_in')

    def amount_1_out(self):
        return self.execution.get('amount_1_out')

    def liquidity(self):
        return self.execution.get('liquidity')

    def executed_at_micros(self):
        return self.execution.get('executed_at_micros')

    def transaction_id(self):
        return self.execution.get('transaction_id')

    def owner_account(self) -> dict[str, object]:
        owner_account = self.execution.get('from')
        if not isinstance(owner_account, dict):
            return {}
        return owner_account

    def normalized_execution_payload(self) -> dict[str, object]:
        return dict(self.execution)
