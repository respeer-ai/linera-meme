from time_codec import TimeCodec


class PoolNewTransactionExecutionFact:
    TRADE_TYPES = {'BuyToken0', 'SellToken0'}
    LIQUIDITY_TYPES = {'AddLiquidity', 'RemoveLiquidity'}

    def __init__(
        self,
        *,
        transaction: dict[str, object],
        application_id: str,
        pool_chain_id: str | None,
        block_hash: str | None,
        normalized_event_id: str,
        transaction_index: int | None,
        event_family: str | None,
    ):
        self.transaction = transaction
        self.application_id = application_id
        self.pool_chain_id = pool_chain_id
        self.block_hash = block_hash
        self.normalized_event_id = normalized_event_id
        self.transaction_index = transaction_index
        self.event_family = event_family
        self.time_codec = TimeCodec()

    def transaction_type(self) -> str | None:
        value = self.transaction.get('transaction_type')
        if value is None:
            return None
        return str(value)

    def transaction_id(self) -> int | None:
        value = self.transaction.get('transaction_id')
        if value is None:
            return None
        return int(value)

    def trade_time_ms(self) -> int | None:
        return self.time_codec.event_time_ms_from_transaction(self.transaction)

    def owner_account(self) -> dict[str, object]:
        value = self.transaction.get('from')
        if not isinstance(value, dict):
            return {}
        return value

    def owner_chain_id(self) -> str | None:
        value = self.owner_account().get('chain_id')
        if value is None:
            value = self._chain_id_from_account_string(self._explicit_from_account())
        if value is None:
            value = self._chain_id_from_position_owner()
        if value is None:
            return None
        return str(value)

    def owner(self) -> str | None:
        value = self.owner_account().get('owner')
        if value is None:
            value = self._owner_from_account_string(self._explicit_from_account())
        if value is None:
            value = self._owner_from_position_owner()
        if value is None:
            return None
        return str(value)

    def from_account(self) -> str | None:
        explicit = self._explicit_from_account()
        if explicit not in (None, ''):
            return explicit
        owner_account = self.owner_account()
        owner_chain_id = owner_account.get('chain_id')
        owner = owner_account.get('owner')
        if owner_chain_id is None or owner is None:
            return None
        return f'{owner_chain_id}:{owner}'

    def position_owner(self) -> str:
        explicit = self.transaction.get('owner')
        if isinstance(explicit, str) and '@' in explicit:
            return explicit
        owner_chain_id = self.owner_chain_id() or 'unknown_chain'
        owner = self.owner() or 'unknown_owner'
        return f'{owner}@{owner_chain_id}'

    def amount_0_in(self):
        return self.transaction.get('amount_0_in')

    def amount_0_out(self):
        return self.transaction.get('amount_0_out')

    def amount_1_in(self):
        return self.transaction.get('amount_1_in')

    def amount_1_out(self):
        return self.transaction.get('amount_1_out')

    def liquidity(self):
        return self.transaction.get('liquidity')

    def is_trade(self) -> bool:
        return self.transaction_type() in self.TRADE_TYPES

    def is_liquidity_change(self) -> bool:
        return self.transaction_type() in self.LIQUIDITY_TYPES

    def event_payload(self) -> dict[str, object]:
        return {
            'transaction': self.transaction,
            'event_family': self.event_family,
        }

    def _chain_id_from_position_owner(self) -> str | None:
        owner = self.transaction.get('owner')
        if not isinstance(owner, str) or '@' not in owner:
            return None
        _, chain_id = owner.split('@', 1)
        return chain_id or None

    def _owner_from_position_owner(self) -> str | None:
        owner = self.transaction.get('owner')
        if not isinstance(owner, str) or '@' not in owner:
            return None
        owner_id, _ = owner.split('@', 1)
        return owner_id or None

    def _chain_id_from_account_string(self, account: str | None) -> str | None:
        if not isinstance(account, str) or ':' not in account:
            return None
        chain_id, _ = account.split(':', 1)
        return chain_id or None

    def _owner_from_account_string(self, account: str | None) -> str | None:
        if not isinstance(account, str) or ':' not in account:
            return None
        _, owner = account.split(':', 1)
        return owner or None

    def _explicit_from_account(self) -> str | None:
        value = self.transaction.get('from_account')
        if value in (None, ''):
            return None
        return str(value)
