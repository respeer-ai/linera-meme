class AccountCodec:
    def payload_account_from_public_account(self, account: str) -> dict[str, str]:
        if ':' not in account:
            raise ValueError('invalid_public_account')
        chain_id, owner = account.split(':', 1)
        if chain_id == '' or owner == '':
            raise ValueError('invalid_public_account')
        return {
            'chain_id': chain_id,
            'owner': owner,
        }

    def public_account_from_payload(self, account: object) -> str | None:
        if isinstance(account, str):
            if ':' in account:
                return account
            return self.public_account_from_settled_owner(account)
        if not isinstance(account, dict):
            return None
        chain_id = account.get('chain_id')
        owner = account.get('owner')
        if chain_id in (None, '') or owner in (None, ''):
            return None
        return f'{chain_id}:{owner}'

    def settled_owner_from_public_account(self, owner: str) -> str:
        chain_id, owner_id = owner.split(':', 1)
        return f'{owner_id}@{chain_id}'

    def public_account_from_settled_owner(self, owner: object) -> str | None:
        if not isinstance(owner, str) or '@' not in owner:
            return None
        owner_id, chain_id = owner.split('@', 1)
        if owner_id == '' or chain_id == '':
            return None
        return f'{chain_id}:{owner_id}'

    def payload_from_public_account(self, account: str | None) -> dict[str, str] | None:
        if account is None:
            return None
        try:
            return self.payload_account_from_public_account(account)
        except ValueError:
            return None
