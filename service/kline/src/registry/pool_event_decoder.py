from registry.rust_decoder_runner import RustDecoderRunner


class PoolEventDecoder:
    VERSION = 'pool-event-rust-v1'

    def __init__(self, runner: RustDecoderRunner | None = None):
        self.runner = runner or RustDecoderRunner()

    def decode(self, *, raw_bytes: bytes, application: dict, payload_kind: str) -> dict:
        if payload_kind != 'event':
            raise ValueError(f'unsupported payload_kind: {payload_kind}')
        return self.runner.decode(
            app_type='pool',
            payload_kind=payload_kind,
            application_id=application['application_id'],
            raw_bytes=raw_bytes,
        )

    def decoder_version(self) -> str:
        return self.VERSION
