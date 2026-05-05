from registry.decoded_transaction_payload_normalizer import DecodedTransactionPayloadNormalizer
from registry.rust_decoder_runner import RustDecoderRunner


class SwapMessageDecoder:
    VERSION = 'swap-message-rust-v1'

    def __init__(self, runner: RustDecoderRunner | None = None):
        self.runner = runner or RustDecoderRunner()
        self.normalizer = DecodedTransactionPayloadNormalizer()

    def decode(self, *, raw_bytes: bytes, application: dict, payload_kind: str) -> dict:
        if payload_kind != 'message':
            raise ValueError(f'unsupported payload_kind: {payload_kind}')
        try:
            decoded = self.runner.decode(
                app_type='swap',
                payload_kind=payload_kind,
                application_id=application['application_id'],
                raw_bytes=raw_bytes,
            )
            decoded['decoded_payload_json'] = self.normalizer.normalize(decoded.get('decoded_payload_json'))
            return decoded
        except ValueError as error:
            if 'expected variant index' in str(error):
                raise ValueError('unsupported swap message variant') from error
            raise

    def decoder_version(self) -> str:
        return self.VERSION
