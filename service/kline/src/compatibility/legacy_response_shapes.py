def preserve_legacy_shape(payload: dict) -> dict:
    """Return a payload using the existing response envelope unchanged."""
    if isinstance(payload, dict):
        return dict(payload)
    return payload
