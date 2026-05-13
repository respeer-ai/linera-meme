class TransactionFamilyCodec:
    TRADE_TYPES = {'BuyToken0', 'SellToken0'}
    LIQUIDITY_TYPES = {'AddLiquidity', 'RemoveLiquidity'}

    def trade_side_from_transaction_type(self, transaction_type: str) -> str | None:
        return {
            'BuyToken0': 'buy_token_0',
            'SellToken0': 'sell_token_0',
        }.get(transaction_type)

    def transaction_type_from_trade_side(self, side: str) -> str:
        return {
            'buy_token_0': 'BuyToken0',
            'sell_token_0': 'SellToken0',
        }[side]

    def liquidity_change_type_from_transaction_type(self, transaction_type: str) -> str | None:
        return {
            'AddLiquidity': 'add_liquidity',
            'RemoveLiquidity': 'remove_liquidity',
        }.get(transaction_type)

    def transaction_type_from_liquidity_change_type(self, change_type: str) -> str:
        return {
            'add_liquidity': 'AddLiquidity',
            'remove_liquidity': 'RemoveLiquidity',
        }[change_type]

    def trade_direction(self, transaction_type: str, *, token_reversed: bool) -> str:
        if transaction_type == 'BuyToken0':
            return 'Sell' if token_reversed else 'Buy'
        if transaction_type == 'SellToken0':
            return 'Buy' if token_reversed else 'Sell'
        raise KeyError(transaction_type)

    def is_trade_transaction_type(self, transaction_type: str | None) -> bool:
        return transaction_type in self.TRADE_TYPES

    def is_liquidity_transaction_type(self, transaction_type: str | None) -> bool:
        return transaction_type in self.LIQUIDITY_TYPES
