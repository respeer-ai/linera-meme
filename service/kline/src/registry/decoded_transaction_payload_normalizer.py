class DecodedTransactionPayloadNormalizer:
    TRANSACTION_TYPE_MAP = {
        'add_liquidity': 'AddLiquidity',
        'remove_liquidity': 'RemoveLiquidity',
        'buy_token_0': 'BuyToken0',
        'sell_token_0': 'SellToken0',
    }

    def normalize(self, payload: object) -> object:
        if isinstance(payload, dict):
            normalized = {}
            for key, value in payload.items():
                if key == 'transaction' and isinstance(value, dict):
                    normalized[key] = self._normalize_transaction(dict(value))
                    continue
                normalized[key] = self.normalize(value)
            return normalized
        if isinstance(payload, list):
            return [self.normalize(item) for item in payload]
        return payload

    def _normalize_transaction(self, transaction: dict[str, object]) -> dict[str, object]:
        normalized = {}
        for key, value in transaction.items():
            if key == 'transaction_type' and value is not None:
                normalized[key] = self.TRANSACTION_TYPE_MAP.get(str(value), value)
                continue
            normalized[key] = self.normalize(value)
        return normalized
