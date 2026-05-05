class TransactionsSerializer:
    def serialize_transactions(self, payload):
        if isinstance(payload, list):
            return [dict(item) if isinstance(item, dict) else item for item in payload]
        if isinstance(payload, dict):
            return dict(payload)
        return payload

    def serialize_information(self, payload: dict) -> dict:
        if isinstance(payload, dict):
            return dict(payload)
        return payload
