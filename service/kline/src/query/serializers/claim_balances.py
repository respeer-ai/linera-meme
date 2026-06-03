class ClaimBalancesSerializer:
    ALLOWED_FIELDS = frozenset({
        'pool_application_id',
        'execution_chain_id',
        'token',
        'owner',
        'claimable_amount',
        'claiming_amount',
        'latest_block_height',
        'latest_transaction_index',
        'latest_message_index',
    })

    def serialize_claim_balances(self, payload: dict) -> dict:
        return {
            'owner': payload.get('owner', ''),
            'balances': self._filter_fields(payload.get('balances', [])),
        }

    def _filter_fields(self, items: list) -> list:
        return [
            {key: item.get(key) for key in self.ALLOWED_FIELDS}
            for item in items
        ]
