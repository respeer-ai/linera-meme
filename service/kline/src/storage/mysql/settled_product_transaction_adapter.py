from decimal import Decimal

from account_codec import AccountCodec
from transaction_family_codec import TransactionFamilyCodec


class SettledProductTransactionAdapter:
    DISPLAY_AMOUNT_SCALE = Decimal('1000000000000000000')

    def __init__(self, *, account_codec=None, transaction_family_codec=None):
        self.account_codec = account_codec or AccountCodec()
        self.transaction_family_codec = transaction_family_codec or TransactionFamilyCodec()

    def build_trade_history_row(self, row: dict[str, object]) -> dict[str, object]:
        return {
            'transaction_id': self._int_or_none(row.get('transaction_id')),
            'transaction_type': self.trade_transaction_type(str(row.get('side') or '')),
            'amount_0_in': self._display_string_or_none(row.get('amount_0_in')),
            'amount_0_out': self._display_string_or_none(row.get('amount_0_out')),
            'amount_1_in': self._display_string_or_none(row.get('amount_1_in')),
            'amount_1_out': self._display_string_or_none(row.get('amount_1_out')),
            'liquidity': None,
            'created_at': self._int_or_none(row.get('trade_time_ms')),
            'from_account': self._string_or_none(row.get('from_account')),
        }

    def build_liquidity_history_row(self, row: dict[str, object]) -> dict[str, object]:
        change_type = str(row.get('change_type') or '')
        is_add = change_type == 'add_liquidity'
        amount_0_delta = self._string_or_none(row.get('amount_0_delta'))
        amount_1_delta = self._string_or_none(row.get('amount_1_delta'))
        return {
            'transaction_id': self._int_or_none(row.get('transaction_id')),
            'transaction_type': self.transaction_family_codec.transaction_type_from_liquidity_change_type(change_type),
            'amount_0_in': self._display_string_or_none(amount_0_delta) if is_add else None,
            'amount_0_out': None if is_add else self._display_string_or_none(amount_0_delta),
            'amount_1_in': self._display_string_or_none(amount_1_delta) if is_add else None,
            'amount_1_out': None if is_add else self._display_string_or_none(amount_1_delta),
            'liquidity': self._display_string_or_none(row.get('liquidity_delta')),
            'created_at': self._int_or_none(row.get('event_time_ms')),
            'from_account': self.public_owner_from_settled_owner(row.get('owner')),
        }

    def trade_transaction_type(self, side: str) -> str:
        return self.transaction_family_codec.transaction_type_from_trade_side(side)

    def settled_owner_from_public_owner(self, owner: str) -> str:
        return self.account_codec.settled_owner_from_public_account(owner)

    def public_owner_from_settled_owner(self, owner: object) -> str | None:
        return self.account_codec.public_account_from_settled_owner(owner)

    def account_payload_to_string(self, account: object) -> str | None:
        return self.account_codec.public_account_from_payload(account)

    def _string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def _display_string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        normalized = format((Decimal(str(value)) / self.DISPLAY_AMOUNT_SCALE).normalize(), 'f')
        if '.' in normalized:
            normalized = normalized.rstrip('0').rstrip('.')
        if normalized in {'', '-0'}:
            return '0'
        return normalized

    def _int_or_none(self, value: object) -> int | None:
        if value is None:
            return None
        return int(value)
