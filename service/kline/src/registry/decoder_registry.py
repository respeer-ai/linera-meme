class DecoderRegistry:
    """Maps app_type and payload_kind pairs to in-process decoder implementations."""

    def __init__(self, registrations: tuple[dict, ...] = ()):
        self._decoders: dict[tuple[str, str], object] = {}
        for registration in registrations:
            self.register(
                app_type=registration['app_type'],
                payload_kind=registration['payload_kind'],
                decoder=registration.get('decoder'),
            )

    def register(self, *, app_type: str, payload_kind: str, decoder) -> None:
        self._decoders[(str(app_type), str(payload_kind))] = decoder

    def resolve(self, *, app_type: str, payload_kind: str):
        return self._decoders.get((str(app_type), str(payload_kind)))

    def list_supported_pairs(self) -> list[dict]:
        return [
            {
                'app_type': app_type,
                'payload_kind': payload_kind,
                'implemented': decoder is not None,
            }
            for (app_type, payload_kind), decoder in sorted(self._decoders.items())
        ]
