from market.pool_new_transaction_execution_fact import PoolNewTransactionExecutionFact


class PoolNewTransactionExecutionFactExtractor:
    REQUIRED_EVENT_KEYS = {
        'normalized_event_id',
        'application_id',
    }

    def extract(self, event: dict[str, object]) -> PoolNewTransactionExecutionFact | None:
        missing = sorted(self.REQUIRED_EVENT_KEYS - set(event.keys()))
        if missing:
            raise ValueError(f'missing execution fact event keys: {",".join(missing)}')
        transaction = self._transaction_payload(event)
        if transaction is None:
            return None
        return PoolNewTransactionExecutionFact(
            transaction=transaction,
            application_id=str(event['application_id']),
            pool_chain_id=self._pool_chain_id(event),
            block_hash=self._block_hash(event),
            normalized_event_id=str(event['normalized_event_id']),
            transaction_index=self._transaction_index(event),
            event_family=self._event_family(event),
        )

    def _transaction_payload(self, event: dict[str, object]) -> dict[str, object] | None:
        payload = event.get('event_payload_json')
        if not isinstance(payload, dict):
            return None
        decoded_payload = payload.get('decoded_payload_json')
        if not isinstance(decoded_payload, dict):
            return None
        transaction = decoded_payload.get('transaction')
        if not isinstance(transaction, dict):
            return None
        return transaction

    def _pool_chain_id(self, event: dict[str, object]) -> str | None:
        value = event.get('target_chain_id') or event.get('source_chain_id')
        if value is None:
            return None
        return str(value)

    def _block_hash(self, event: dict[str, object]) -> str | None:
        value = event.get('target_block_hash') or event.get('source_block_hash')
        if value is None:
            return None
        return str(value)

    def _transaction_index(self, event: dict[str, object]) -> int | None:
        value = event.get('transaction_index')
        if value is None:
            return None
        return int(value)

    def _event_family(self, event: dict[str, object]) -> str | None:
        value = event.get('event_family')
        if value is None:
            return None
        return str(value)
