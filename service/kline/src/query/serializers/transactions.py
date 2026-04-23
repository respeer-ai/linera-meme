from compatibility.legacy_response_shapes import LegacyResponseShapeAdapter


class TransactionsSerializer:
    def __init__(self):
        self.adapter = LegacyResponseShapeAdapter()

    def serialize_transactions(self, payload):
        if isinstance(payload, list):
            return [self.adapter.preserve(item) for item in payload]
        return self.adapter.preserve(payload)

    def serialize_information(self, payload: dict) -> dict:
        return self.adapter.preserve(payload)
