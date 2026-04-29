from market.settled_market_result import SettledMarketResult


class SettledMarketDeriver:
    def derive_item(self, event: dict[str, object]) -> dict[str, object]:
        self._validate_event(event)
        result = self._derive(event)
        return result.to_dict()

    def derive_batch(self, events: list[dict[str, object]]) -> list[dict[str, object]]:
        return [self.derive_item(event) for event in events]

    def _derive(self, event: dict[str, object]) -> SettledMarketResult:
        if event.get('normalization_status') != 'observed':
            return self._result(
                event,
                derivation_status=SettledMarketResult.STATUS_IGNORED_NON_SETTLED,
            )
        if event.get('event_family') != 'pool_transaction_recorded':
            return self._result(
                event,
                derivation_status=SettledMarketResult.STATUS_IGNORED_NON_SETTLED,
            )
        payload = event.get('event_payload_json') or {}
        decoded_payload = payload.get('decoded_payload_json') or {}
        transaction = decoded_payload.get('transaction')
        if not isinstance(transaction, dict):
            return self._result(
                event,
                derivation_status=SettledMarketResult.STATUS_BLOCKED_MISSING_CONTEXT,
                error_text='missing transaction payload',
            )
        transaction_type = transaction.get('transaction_type')
        if transaction_type in {'buy_token_0', 'sell_token_0'}:
            trade = self._build_trade(event, transaction)
            if trade is None:
                return self._result(
                    event,
                    derivation_status=SettledMarketResult.STATUS_BLOCKED_MISSING_CONTEXT,
                    error_text='trade transaction is missing required amount fields',
                )
            return self._result(
                event,
                derivation_status=SettledMarketResult.STATUS_SETTLED,
                settled_outputs=[trade],
            )
        if transaction_type in {'add_liquidity', 'remove_liquidity'}:
            liquidity_change = self._build_liquidity_change(event, transaction)
            if liquidity_change is None:
                return self._result(
                    event,
                    derivation_status=SettledMarketResult.STATUS_BLOCKED_MISSING_CONTEXT,
                    error_text='liquidity transaction is missing required amount fields',
                )
            return self._result(
                event,
                derivation_status=SettledMarketResult.STATUS_SETTLED,
                settled_outputs=[liquidity_change],
            )
        return self._result(
            event,
            derivation_status=SettledMarketResult.STATUS_INCONSISTENT_SOURCE,
            error_text=f'unsupported transaction_type: {transaction_type}',
        )

    def _build_trade(
        self,
        event: dict[str, object],
        transaction: dict[str, object],
    ) -> dict[str, object] | None:
        transaction_type = transaction.get('transaction_type')
        amount_0_in = transaction.get('amount_0_in')
        amount_0_out = transaction.get('amount_0_out')
        amount_1_in = transaction.get('amount_1_in')
        amount_1_out = transaction.get('amount_1_out')
        if transaction_type == 'buy_token_0':
            amount_in = amount_1_in
            amount_out = amount_0_out
            price_numerator = amount_1_in
            price_denominator = amount_0_out
            side = 'buy_token_0'
        else:
            amount_in = amount_0_in
            amount_out = amount_1_out
            price_numerator = amount_1_out
            price_denominator = amount_0_in
            side = 'sell_token_0'
        if None in (amount_in, amount_out, price_numerator, price_denominator):
            return None
        return {
            'settled_output_type': SettledMarketResult.OUTPUT_SETTLED_TRADE,
            'settled_trade_id': f"{event['normalized_event_id']}:trade",
            'normalized_event_id': event['normalized_event_id'],
            'pool_application_id': event['application_id'],
            'pool_chain_id': event.get('target_chain_id') or event.get('source_chain_id'),
            'block_hash': event.get('target_block_hash') or event.get('source_block_hash'),
            'trade_time_ms': self._to_millis(transaction.get('created_at_micros')),
            'transaction_index': event.get('transaction_index'),
            'transaction_id': transaction.get('transaction_id'),
            'side': side,
            'amount_in': str(amount_in),
            'amount_out': str(amount_out),
            'price_numerator': str(price_numerator),
            'price_denominator': str(price_denominator),
            'source_event_key': event['normalized_event_id'],
            'event_payload_json': {
                'transaction': transaction,
                'event_family': event.get('event_family'),
            },
        }

    def _build_liquidity_change(
        self,
        event: dict[str, object],
        transaction: dict[str, object],
    ) -> dict[str, object] | None:
        amount_0_delta = transaction.get('amount_0_in')
        amount_1_delta = transaction.get('amount_1_in')
        liquidity_delta = transaction.get('liquidity')
        if None in (amount_0_delta, amount_1_delta, liquidity_delta):
            return None
        owner_account = transaction.get('from') or {}
        owner_chain_id = owner_account.get('chain_id') or 'unknown_chain'
        owner = owner_account.get('owner') or 'unknown_owner'
        return {
            'settled_output_type': SettledMarketResult.OUTPUT_SETTLED_LIQUIDITY_CHANGE,
            'settled_liquidity_change_id': f"{event['normalized_event_id']}:liquidity",
            'normalized_event_id': event['normalized_event_id'],
            'pool_application_id': event['application_id'],
            'pool_chain_id': event.get('target_chain_id') or event.get('source_chain_id'),
            'owner': f'{owner}@{owner_chain_id}',
            'block_hash': event.get('target_block_hash') or event.get('source_block_hash'),
            'event_time_ms': self._to_millis(transaction.get('created_at_micros')),
            'transaction_index': event.get('transaction_index'),
            'transaction_id': transaction.get('transaction_id'),
            'change_type': str(transaction.get('transaction_type')),
            'liquidity_delta': str(liquidity_delta),
            'amount_0_delta': str(amount_0_delta),
            'amount_1_delta': str(amount_1_delta),
            'source_event_key': event['normalized_event_id'],
            'event_payload_json': {
                'transaction': transaction,
                'event_family': event.get('event_family'),
            },
        }

    def _result(
        self,
        event: dict[str, object],
        *,
        derivation_status: str,
        settled_outputs: list[dict[str, object]] | None = None,
        error_text: str | None = None,
    ) -> SettledMarketResult:
        return SettledMarketResult(
            normalized_event_id=event['normalized_event_id'],
            source_event_key=event['normalized_event_id'],
            derivation_status=derivation_status,
            settled_outputs=settled_outputs,
            error_text=error_text,
        )

    def _to_millis(self, micros: object) -> int | None:
        if micros is None:
            return None
        return int(micros) // 1000

    def _validate_event(self, event: dict[str, object]) -> None:
        required_keys = {
            'normalized_event_id',
            'application_id',
            'event_family',
            'normalization_status',
        }
        missing = sorted(required_keys - set(event.keys()))
        if missing:
            raise ValueError(f'missing market derivation event keys: {",".join(missing)}')
