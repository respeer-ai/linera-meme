from compatibility.legacy_response_shapes import LegacyResponseShapeAdapter


class PositionsSerializer:
    def __init__(self):
        self.adapter = LegacyResponseShapeAdapter()

    def serialize_positions(self, payload: dict) -> dict:
        return self.adapter.preserve(payload)
