import base64
import json


class CanonicalFingerprint:
    """Builds stable content fingerprints for Layer 1 replay and conflict checks."""

    def build(self, payload) -> str:
        return self.build_json(payload)

    def build_json(self, payload) -> str:
        return json.dumps(
            self._normalize(payload),
            ensure_ascii=True,
            sort_keys=True,
            separators=(',', ':'),
        )

    def build_bytes(self, payload) -> bytes:
        return self.build_json(payload).encode('ascii')

    def _normalize(self, payload):
        if isinstance(payload, dict):
            return {
                str(key): self._normalize(value)
                for key, value in sorted(payload.items(), key=lambda item: str(item[0]))
            }
        if isinstance(payload, (list, tuple)):
            return [self._normalize(item) for item in payload]
        if isinstance(payload, (bytes, bytearray, memoryview)):
            return {
                '__type__': 'bytes',
                'base64': base64.b64encode(bytes(payload)).decode('ascii'),
            }
        return payload
