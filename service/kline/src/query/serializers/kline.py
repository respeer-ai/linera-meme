from compatibility.legacy_response_shapes import preserve_legacy_shape


class KlineSerializer:
    def serialize_points(self, payload: dict) -> dict:
        return preserve_legacy_shape(payload)

    def serialize_information(self, payload: dict) -> dict:
        return preserve_legacy_shape(payload)
