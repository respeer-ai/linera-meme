import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from registry.ams_message_decoder import AmsMessageDecoder  # noqa: E402
from registry.blob_gateway_message_decoder import BlobGatewayMessageDecoder  # noqa: E402
from registry.pool_event_decoder import PoolEventDecoder  # noqa: E402
from registry.proxy_message_decoder import ProxyMessageDecoder  # noqa: E402


class MessageDecoderRegistrationTest(unittest.TestCase):
    class FakeRunner:
        def __init__(self, expected_app_type: str):
            self.expected_app_type = expected_app_type

        def decode(self, *, app_type: str, payload_kind: str, application_id: str, raw_bytes: bytes) -> dict:
            if app_type != self.expected_app_type:
                raise AssertionError(f'unexpected app_type: {app_type}')
            return {
                'payload_type': 'register',
                'decoded_payload_json': {
                    'application_id': application_id,
                    'payload_kind': payload_kind,
                    'raw_bytes_hex': raw_bytes.hex(),
                },
                'decoder_version': f'{app_type}-message-rust-v1',
            }

    def test_proxy_message_decoder_uses_canonical_runner(self):
        decoder = ProxyMessageDecoder(runner=self.FakeRunner('proxy'))

        decoded = decoder.decode(
            raw_bytes=b'\x00\x01',
            application={'application_id': 'app-proxy'},
            payload_kind='message',
        )

        self.assertEqual(decoded['payload_type'], 'register')
        self.assertEqual(decoded['decoder_version'], 'proxy-message-rust-v1')

    def test_ams_message_decoder_uses_canonical_runner(self):
        decoder = AmsMessageDecoder(runner=self.FakeRunner('ams'))

        decoded = decoder.decode(
            raw_bytes=b'\x02\x03',
            application={'application_id': 'app-ams'},
            payload_kind='message',
        )

        self.assertEqual(decoded['payload_type'], 'register')
        self.assertEqual(decoded['decoder_version'], 'ams-message-rust-v1')

    def test_blob_gateway_message_decoder_uses_canonical_runner(self):
        decoder = BlobGatewayMessageDecoder(runner=self.FakeRunner('blob-gateway'))

        decoded = decoder.decode(
            raw_bytes=b'\x04\x05',
            application={'application_id': 'app-blob'},
            payload_kind='message',
        )

        self.assertEqual(decoded['payload_type'], 'register')
        self.assertEqual(decoded['decoder_version'], 'blob-gateway-message-rust-v1')

    def test_pool_event_decoder_uses_canonical_runner(self):
        decoder = PoolEventDecoder(runner=self.FakeRunner('pool'))

        decoded = decoder.decode(
            raw_bytes=b'\x06\x07',
            application={'application_id': 'app-pool'},
            payload_kind='event',
        )

        self.assertEqual(decoded['payload_type'], 'register')
        self.assertEqual(decoded['decoder_version'], 'pool-message-rust-v1')
