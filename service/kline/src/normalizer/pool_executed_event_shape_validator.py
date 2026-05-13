class PoolExecutedEventShapeValidator:
    TRADE_TYPES = {'buy_token_0', 'sell_token_0'}
    CHANGE_TYPES = {'add_liquidity', 'remove_liquidity'}
    EXECUTED_EVENT_TYPES = {
        'swap_executed',
        'add_liquidity_executed',
        'remove_liquidity_executed',
    }

    def validate(self, decode_result: dict[str, object]) -> str | None:
        if decode_result.get('app_type') != 'pool':
            return None
        if decode_result.get('payload_kind') != 'event':
            return None
        payload_type = decode_result.get('payload_type')
        if payload_type not in self.EXECUTED_EVENT_TYPES:
            return None
        decoded_payload = decode_result.get('decoded_payload_json')
        if not isinstance(decoded_payload, dict):
            return 'decoded payload must be an object'
        execution = decoded_payload.get('execution')
        if not isinstance(execution, dict):
            return 'decoded payload is missing execution object'
        error = self._validate_common_fields(execution)
        if error is not None:
            return error
        if payload_type == 'swap_executed':
            return self._validate_trade_execution(execution)
        return self._validate_liquidity_execution(execution)

    def _validate_common_fields(self, execution: dict[str, object]) -> str | None:
        if execution.get('transaction_id') is None:
            return 'execution.transaction_id is required'
        if execution.get('executed_at_micros') is None:
            return 'execution.executed_at_micros is required'
        owner_account = execution.get('from')
        if not isinstance(owner_account, dict):
            return 'execution.from must be an object'
        if owner_account.get('chain_id') is None:
            return 'execution.from.chain_id is required'
        if owner_account.get('owner') is None:
            return 'execution.from.owner is required'
        return None

    def _validate_trade_execution(self, execution: dict[str, object]) -> str | None:
        trade_type = execution.get('trade_type')
        if trade_type not in self.TRADE_TYPES:
            return 'execution.trade_type is invalid'
        if trade_type == 'buy_token_0':
            if execution.get('amount_1_in') is None:
                return 'buy execution.amount_1_in is required'
            if execution.get('amount_0_out') is None:
                return 'buy execution.amount_0_out is required'
            return None
        if execution.get('amount_0_in') is None:
            return 'sell execution.amount_0_in is required'
        if execution.get('amount_1_out') is None:
            return 'sell execution.amount_1_out is required'
        return None

    def _validate_liquidity_execution(self, execution: dict[str, object]) -> str | None:
        change_type = execution.get('change_type')
        if change_type not in self.CHANGE_TYPES:
            return 'execution.change_type is invalid'
        if execution.get('liquidity') is None:
            return 'execution.liquidity is required'
        if change_type == 'add_liquidity':
            if execution.get('amount_0_in') is None:
                return 'add execution.amount_0_in is required'
            if execution.get('amount_1_in') is None:
                return 'add execution.amount_1_in is required'
            return None
        if execution.get('amount_0_out') is None:
            return 'remove execution.amount_0_out is required'
        if execution.get('amount_1_out') is None:
            return 'remove execution.amount_1_out is required'
        return None
