class LegacyResponseShapeAdapter:
    """Return payloads using the existing response envelope unchanged."""

    def preserve(self, payload):
        if isinstance(payload, dict):
            return dict(payload)
        return payload
