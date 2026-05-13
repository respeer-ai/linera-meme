class AccountCodec:
    CHAIN_OWNER = '0x00'

    def format_owner(self, owner: object | None) -> str:
        if owner in (None, ''):
            return self.CHAIN_OWNER
        owner_value = str(owner)
        if not owner_value.startswith('0x'):
            raise ValueError('invalid_account_owner')
        suffix = owner_value[2:]
        if suffix == '' or not all(char in '0123456789abcdefABCDEF' for char in suffix):
            raise ValueError('invalid_account_owner')
        return f'0x{suffix.lower()}'

    def format_account(self, *, chain_id: object, owner: object | None = None) -> str:
        chain_id_value = self._chain_id(chain_id)
        return f'{self.format_owner(owner)}@{chain_id_value}'

    def parse_account(self, account: object) -> dict[str, str]:
        if not isinstance(account, str):
            raise ValueError('invalid_public_account')
        if ':' in account:
            raise ValueError('invalid_public_account')
        if '@' not in account:
            return {
                'chain_id': self._chain_id(account),
                'owner': self.CHAIN_OWNER,
            }
        owner, chain_id = account.split('@', 1)
        return {
            'chain_id': self._chain_id(chain_id),
            'owner': self.format_owner(owner),
        }

    def application_id_from_account(self, account: object) -> str:
        owner = self.parse_account(account)['owner']
        if owner == self.CHAIN_OWNER:
            raise ValueError('invalid_application_account')
        return owner[2:]

    def chain_id_from_account(self, account: object) -> str:
        return self.parse_account(account)['chain_id']

    def payload_account_from_public_account(self, account: str) -> dict[str, str]:
        return self.parse_account(account)

    def public_account_from_payload(self, account: object) -> str | None:
        if isinstance(account, str):
            try:
                parsed = self.parse_account(account)
                return self.format_account(chain_id=parsed['chain_id'], owner=parsed['owner'])
            except ValueError:
                return None
        if not isinstance(account, dict):
            return None
        chain_id = account.get('chain_id')
        if chain_id is None:
            chain_id = account.get('chainId')
        owner = account.get('owner')
        if chain_id in (None, ''):
            return None
        try:
            return self.format_account(chain_id=chain_id, owner=owner)
        except ValueError:
            return None

    def settled_owner_from_public_account(self, owner: str) -> str:
        parsed = self.parse_account(owner)
        return self.format_account(chain_id=parsed['chain_id'], owner=parsed['owner'])

    def public_account_from_settled_owner(self, owner: object) -> str | None:
        if not isinstance(owner, str):
            return None
        try:
            parsed = self.parse_account(owner)
            if parsed['owner'] == self.CHAIN_OWNER:
                return None
            return self.format_account(chain_id=parsed['chain_id'], owner=parsed['owner'])
        except ValueError:
            return None

    def payload_from_public_account(self, account: str | None) -> dict[str, str] | None:
        if account is None:
            return None
        try:
            return self.payload_account_from_public_account(account)
        except ValueError:
            return None

    def _chain_id(self, chain_id: object) -> str:
        if chain_id in (None, ''):
            raise ValueError('invalid_chain_id')
        return str(chain_id)
