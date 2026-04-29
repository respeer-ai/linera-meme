from compatibility.legacy_response_shapes import LegacyResponseShapeAdapter


class PositionMetricsSerializer:
    def __init__(self):
        self.adapter = LegacyResponseShapeAdapter()

    def serialize_position_metrics(self, payload: dict) -> dict:
        return self.adapter.preserve(payload)
