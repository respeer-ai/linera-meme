from compatibility.legacy_response_shapes import preserve_legacy_shape


class PositionsSerializer:
    def serialize_positions(self, payload: dict) -> dict:
        return preserve_legacy_shape(payload)
