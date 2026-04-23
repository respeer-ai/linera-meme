from compatibility.legacy_response_shapes import preserve_legacy_shape


class TransactionsSerializer:
    def serialize_transactions(self, payload):
        if isinstance(payload, list):
            return [preserve_legacy_shape(item) for item in payload]
        return preserve_legacy_shape(payload)

    def serialize_information(self, payload: dict) -> dict:
        return preserve_legacy_shape(payload)
