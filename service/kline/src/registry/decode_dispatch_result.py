class DecodeDispatchResult:
    STATUS_DECODED = 'decoded'
    STATUS_UNRESOLVED_APPLICATION = 'unresolved_application'
    STATUS_UNIMPLEMENTED_DECODER = 'unimplemented_decoder'
    STATUS_DECODE_FAILED = 'decode_failed'

    def __init__(
        self,
        *,
        status: str,
        application_id: str,
        payload_kind: str,
        app_type: str | None = None,
        payload_type: str | None = None,
        decoded_payload_json: dict | list | str | int | float | bool | None = None,
        decode_error: str | None = None,
        metadata_json: dict | None = None,
        decoder_version: str | None = None,
    ):
        self.status = status
        self.application_id = application_id
        self.payload_kind = payload_kind
        self.app_type = app_type
        self.payload_type = payload_type
        self.decoded_payload_json = decoded_payload_json
        self.decode_error = decode_error
        self.metadata_json = metadata_json
        self.decoder_version = decoder_version

    def to_dict(self) -> dict[str, object]:
        return {
            'status': self.status,
            'application_id': self.application_id,
            'payload_kind': self.payload_kind,
            'app_type': self.app_type,
            'payload_type': self.payload_type,
            'decoded_payload_json': self.decoded_payload_json,
            'decode_error': self.decode_error,
            'metadata_json': self.metadata_json,
            'decoder_version': self.decoder_version,
        }
