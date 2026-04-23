from compatibility.legacy_response_shapes import LegacyResponseShapeAdapter


class KlineSerializer:
    def __init__(self):
        self.adapter = LegacyResponseShapeAdapter()

    def serialize_points(self, payload: dict) -> dict:
        return self.adapter.preserve(payload)

    def serialize_information(self, payload: dict) -> dict:
        return self.adapter.preserve(payload)
