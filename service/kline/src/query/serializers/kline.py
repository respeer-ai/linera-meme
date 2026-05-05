class KlineSerializer:
    def serialize_points(self, payload: dict) -> dict:
        if isinstance(payload, dict):
            return dict(payload)
        return payload

    def serialize_information(self, payload: dict) -> dict:
        if isinstance(payload, dict):
            return dict(payload)
        return payload
