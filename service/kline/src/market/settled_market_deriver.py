from market.settled_market_result import SettledMarketResult
from market.pool_new_transaction_execution_fact_extractor import PoolNewTransactionExecutionFactExtractor
from transaction_family_codec import TransactionFamilyCodec


class SettledMarketDeriver:
    SETTLED_EVENT_FAMILY = 'pool_new_transaction_recorded'

    def __init__(
        self,
        *,
        execution_fact_extractor=None,
        transaction_family_codec=None,
    ):
        self.execution_fact_extractor = (
            execution_fact_extractor
            or PoolNewTransactionExecutionFactExtractor()
        )
        self.transaction_family_codec = transaction_family_codec or TransactionFamilyCodec()

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
        if event.get('event_family') != self.SETTLED_EVENT_FAMILY:
            return self._result(
                event,
                derivation_status=SettledMarketResult.STATUS_IGNORED_NON_SETTLED,
            )
        execution_fact = self.execution_fact_extractor.extract(event)
        if execution_fact is None:
            return self._result(
                event,
                derivation_status=SettledMarketResult.STATUS_BLOCKED_MISSING_CONTEXT,
                error_text='missing transaction payload',
            )
        if execution_fact.is_trade():
            trade = self._build_trade(execution_fact)
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
        if execution_fact.is_liquidity_change():
            liquidity_change = self._build_liquidity_change(execution_fact)
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
        transaction_type = execution_fact.transaction_type()
        return self._result(
            event,
            derivation_status=SettledMarketResult.STATUS_INCONSISTENT_SOURCE,
            error_text=f'unsupported pool transaction type: {transaction_type}',
        )

    def _build_trade(
        self,
        execution_fact,
    ) -> dict[str, object] | None:
        transaction_type = execution_fact.transaction_type()
        amount_0_in = execution_fact.amount_0_in()
        amount_0_out = execution_fact.amount_0_out()
        amount_1_in = execution_fact.amount_1_in()
        amount_1_out = execution_fact.amount_1_out()
        if transaction_type == 'BuyToken0':
            amount_in = amount_1_in
            amount_out = amount_0_out
            price_numerator = amount_1_in
            price_denominator = amount_0_out
        elif transaction_type == 'SellToken0':
            amount_in = amount_0_in
            amount_out = amount_1_out
            price_numerator = amount_1_out
            price_denominator = amount_0_in
        else:
            return None
        side = self.transaction_family_codec.trade_side_from_transaction_type(transaction_type)
        if None in (amount_in, amount_out, price_numerator, price_denominator):
            return None
        return {
            'settled_output_type': SettledMarketResult.OUTPUT_SETTLED_TRADE,
            'settled_trade_id': f"{execution_fact.normalized_event_id}:trade",
            'normalized_event_id': execution_fact.normalized_event_id,
            'pool_application_id': execution_fact.application_id,
            'pool_chain_id': execution_fact.pool_chain_id,
            'from_account': execution_fact.from_account(),
            'block_hash': execution_fact.block_hash,
            'trade_time_ms': execution_fact.trade_time_ms(),
            'transaction_index': execution_fact.transaction_index,
            'transaction_id': execution_fact.transaction_id(),
            'side': side,
            'amount_0_in': self._string_or_none(amount_0_in),
            'amount_0_out': self._string_or_none(amount_0_out),
            'amount_1_in': self._string_or_none(amount_1_in),
            'amount_1_out': self._string_or_none(amount_1_out),
            'amount_in': str(amount_in),
            'amount_out': str(amount_out),
            'price_numerator': str(price_numerator),
            'price_denominator': str(price_denominator),
            'source_event_key': execution_fact.normalized_event_id,
            'event_payload_json': execution_fact.event_payload(),
        }

    def _build_liquidity_change(
        self,
        execution_fact,
    ) -> dict[str, object] | None:
        transaction_type = execution_fact.transaction_type()
        change_type = self.transaction_family_codec.liquidity_change_type_from_transaction_type(
            str(transaction_type)
        )
        is_add = change_type == 'add_liquidity'
        is_remove = change_type == 'remove_liquidity'
        if not is_add and not is_remove:
            return None
        amount_0_delta = execution_fact.amount_0_in() if is_add else execution_fact.amount_0_out()
        amount_1_delta = execution_fact.amount_1_in() if is_add else execution_fact.amount_1_out()
        liquidity_delta = execution_fact.liquidity()
        if None in (amount_0_delta, amount_1_delta, liquidity_delta):
            return None
        liquidity_semantics = self._liquidity_semantics(
            change_type=change_type,
            liquidity_delta=liquidity_delta,
        )
        return {
            'settled_output_type': SettledMarketResult.OUTPUT_SETTLED_LIQUIDITY_CHANGE,
            'settled_liquidity_change_id': f"{execution_fact.normalized_event_id}:liquidity",
            'normalized_event_id': execution_fact.normalized_event_id,
            'pool_application_id': execution_fact.application_id,
            'pool_chain_id': execution_fact.pool_chain_id,
            'owner': execution_fact.position_owner(),
            'block_hash': execution_fact.block_hash,
            'event_time_ms': execution_fact.trade_time_ms(),
            'transaction_index': execution_fact.transaction_index,
            'transaction_id': execution_fact.transaction_id(),
            'change_type': change_type,
            'liquidity_delta': str(liquidity_delta),
            'is_position_liquidity': liquidity_semantics == 'position_liquidity',
            'liquidity_semantics': liquidity_semantics,
            'amount_0_delta': str(amount_0_delta),
            'amount_1_delta': str(amount_1_delta),
            'source_event_key': execution_fact.normalized_event_id,
            'event_payload_json': execution_fact.event_payload(),
        }

    def _liquidity_semantics(
        self,
        *,
        change_type: str,
        liquidity_delta: object,
    ) -> str:
        if change_type == 'add_liquidity' and str(liquidity_delta) in {'0', '0.0', '0.000000000000000000'}:
            return 'virtual_initial_liquidity'
        return 'position_liquidity'

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

    def _string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

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
