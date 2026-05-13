import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'
TEST_ROOT = ROOT / 'tests'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))


from registry.application_registry import ApplicationRegistry  # noqa: E402
from registry.decoder_dispatcher import DecoderDispatcher  # noqa: E402
from registry.decoder_registry import DecoderRegistry  # noqa: E402
from rust_fixture_loader import RustFixtureLoader  # noqa: E402


class DecoderDispatcherTest(unittest.TestCase):
    FIXTURES = RustFixtureLoader()

    class FakeRepository:
        def __init__(self):
            self.entries = {}

        def upsert_application(self, entry: dict) -> None:
            self.entries[entry['application_id']] = dict(entry)

        def get_application(self, application_id: str) -> dict | None:
            entry = self.entries.get(application_id)
            return None if entry is None else dict(entry)

        def list_applications(self, *, app_type: str | None = None, limit: int = 200) -> list[dict]:
            entries = [dict(entry) for entry in self.entries.values()]
            if app_type is not None:
                entries = [entry for entry in entries if entry['app_type'] == app_type]
            return entries[:limit]

    class SuccessfulDecoder:
        VERSION = 'v1-static'

        def decode(self, *, raw_bytes: bytes, application: dict, payload_kind: str) -> dict:
            return {
                'payload_type': f"{application['app_type']}_{payload_kind}",
                'decoded_payload_json': {
                    'raw_hex': raw_bytes.hex(),
                    'application_id': application['application_id'],
                },
            }

    class FailingDecoder:
        def decoder_version(self) -> str:
            return 'v2-method'

        def decode(self, *, raw_bytes: bytes, application: dict, payload_kind: str) -> dict:
            raise RuntimeError(f'cannot decode {application["app_type"]}:{payload_kind}:{raw_bytes.hex()}')

    def test_dispatch_returns_unresolved_when_application_is_unknown(self):
        registry = ApplicationRegistry(self.FakeRepository())
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=DecoderRegistry(),
        )

        result = dispatcher.dispatch(
            application_id='app-unknown',
            payload_kind='message',
            raw_bytes=b'\x01\x02',
        )

        self.assertEqual(
            result.to_dict(),
            {
                'status': 'unresolved_application',
                'application_id': 'app-unknown',
                'payload_kind': 'message',
                'app_type': None,
                'payload_type': None,
                'decoded_payload_json': None,
                'decode_error': 'application_id is not registered',
                'metadata_json': None,
                'decoder_version': None,
            },
        )

    def test_dispatch_returns_unimplemented_when_decoder_is_missing(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
            metadata_json={'token_0': 'a'},
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register_known_pairs((('pool', 'message'),))
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-pool',
            payload_kind='message',
            raw_bytes=b'\x01',
        )

        self.assertEqual(result.to_dict()['status'], 'unimplemented_decoder')
        self.assertEqual(result.to_dict()['app_type'], 'pool')
        self.assertEqual(result.to_dict()['metadata_json'], {'token_0': 'a'})
        self.assertIsNone(result.to_dict()['decoder_version'])

    def test_dispatch_returns_unimplemented_for_known_pool_event_slot(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register_known_pairs((('pool', 'event'),))
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-pool',
            payload_kind='event',
            raw_bytes=b'\x01',
        )

        self.assertEqual(result.to_dict()['status'], 'unimplemented_decoder')
        self.assertEqual(result.to_dict()['app_type'], 'pool')
        self.assertEqual(result.to_dict()['payload_kind'], 'event')

    def test_dispatch_reports_decode_failed_for_pool_event_when_decoder_exists_but_rust_side_is_unimplemented(self):
        class PoolEventDecoder:
            def decode(self, *, raw_bytes: bytes, application: dict, payload_kind: str) -> dict:
                raise ValueError('pool:event canonical decoding is not implemented')

            def decoder_version(self) -> str:
                return 'pool-event-rust-v1'

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='pool',
            payload_kind='event',
            decoder=PoolEventDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-pool',
            payload_kind='event',
            raw_bytes=b'\x01',
        )

        self.assertEqual(result.to_dict()['status'], 'decode_failed')
        self.assertEqual(result.to_dict()['app_type'], 'pool')
        self.assertEqual(result.to_dict()['payload_kind'], 'event')
        self.assertEqual(result.to_dict()['decoder_version'], 'pool-event-rust-v1')
        self.assertIn('pool:event canonical decoding is not implemented', result.to_dict()['decode_error'])

    def test_dispatch_uses_real_pool_event_decoder_boundary(self):
        from registry.pool_event_decoder import PoolEventDecoder

        class FailingRunner:
            def decode(self, *, app_type: str, payload_kind: str, application_id: str, raw_bytes: bytes) -> dict:
                self.last_call = (app_type, payload_kind, application_id, raw_bytes)
                raise ValueError('pool:event canonical decoding is not implemented')

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
        )
        runner = FailingRunner()
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='pool',
            payload_kind='event',
            decoder=PoolEventDecoder(runner=runner),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-pool',
            payload_kind='event',
            raw_bytes=b'\x09',
        )

        self.assertEqual(
            runner.last_call,
            ('pool', 'event', 'app-pool', b'\x09'),
        )
        self.assertEqual(result.to_dict()['status'], 'decode_failed')
        self.assertEqual(result.to_dict()['decoder_version'], 'pool-event-rust-v1')

    def test_dispatch_returns_decode_failed_when_decoder_raises(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='pool',
            payload_kind='message',
            decoder=self.FailingDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-pool',
            payload_kind='message',
            raw_bytes=b'\xff',
        )

        self.assertEqual(result.to_dict()['status'], 'decode_failed')
        self.assertIn('cannot decode pool:message:ff', result.to_dict()['decode_error'])
        self.assertEqual(result.to_dict()['decoder_version'], 'v2-method')

    def test_dispatch_returns_decoded_payload_when_decoder_succeeds(self):
        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
            metadata_json={'token_0': 'a'},
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='pool',
            payload_kind='message',
            decoder=self.SuccessfulDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-pool',
            payload_kind='message',
            raw_bytes=b'\x0a\x0b',
        )

        self.assertEqual(
            result.to_dict(),
            {
                'status': 'decoded',
                'application_id': 'app-pool',
                'payload_kind': 'message',
                'app_type': 'pool',
                'payload_type': 'pool_message',
                'decoded_payload_json': {
                    'raw_hex': '0a0b',
                    'application_id': 'app-pool',
                },
                'decode_error': None,
                'metadata_json': {'token_0': 'a'},
                'decoder_version': 'v1-static',
            },
        )

    def test_dispatch_decodes_real_blob_gateway_operation(self):
        from registry.blob_gateway_operation_decoder import BlobGatewayOperationDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-blob',
            app_type='blob-gateway',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='blob-gateway',
            payload_kind='operation',
            decoder=BlobGatewayOperationDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        raw_bytes = bytes([0, 1, 2]) + bytes.fromhex('11' * 32)
        result = dispatcher.dispatch(
            application_id='app-blob',
            payload_kind='operation',
            raw_bytes=raw_bytes,
        )

        self.assertEqual(
            result.to_dict(),
            {
                'status': 'decoded',
                'application_id': 'app-blob',
                'payload_kind': 'operation',
                'app_type': 'blob-gateway',
                'payload_type': 'blob_gateway_register',
                'decoded_payload_json': {
                    'operation_type': 'register',
                    'store_type': 'ipfs',
                    'data_type': 'html',
                    'blob_hash_hex': '11' * 32,
                    'application_id': 'app-blob',
                },
                'decode_error': None,
                'metadata_json': None,
                'decoder_version': 'blob-gateway-operation-rust-v1',
            },
        )

    def test_dispatch_decodes_real_proxy_register_miner_operation(self):
        from registry.proxy_operation_decoder import ProxyOperationDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-proxy',
            app_type='proxy',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='proxy',
            payload_kind='operation',
            decoder=ProxyOperationDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-proxy',
            payload_kind='operation',
            raw_bytes=bytes([4]),
        )

        self.assertEqual(
            result.to_dict(),
            {
                'status': 'decoded',
                'application_id': 'app-proxy',
                'payload_kind': 'operation',
                'app_type': 'proxy',
                'payload_type': 'register_miner',
                'decoded_payload_json': {
                    'operation_type': 'register_miner',
                    'application_id': 'app-proxy',
                },
                'decode_error': None,
                'metadata_json': None,
                'decoder_version': 'proxy-operation-rust-v1',
            },
        )

    def test_dispatch_decodes_real_proxy_deregister_miner_operation(self):
        from registry.proxy_operation_decoder import ProxyOperationDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-proxy',
            app_type='proxy',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='proxy',
            payload_kind='operation',
            decoder=ProxyOperationDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-proxy',
            payload_kind='operation',
            raw_bytes=bytes([5]),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'deregister_miner')
        self.assertEqual(result.to_dict()['decoder_version'], 'proxy-operation-rust-v1')

    def test_dispatch_decodes_real_ams_add_application_type_operation(self):
        from registry.ams_operation_decoder import AmsOperationDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-ams',
            app_type='ams',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='ams',
            payload_kind='operation',
            decoder=AmsOperationDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        raw_bytes = bytes([2, 4]) + b'DeFi'
        result = dispatcher.dispatch(
            application_id='app-ams',
            payload_kind='operation',
            raw_bytes=raw_bytes,
        )

        self.assertEqual(
            result.to_dict(),
            {
                'status': 'decoded',
                'application_id': 'app-ams',
                'payload_kind': 'operation',
                'app_type': 'ams',
                'payload_type': 'add_application_type',
                'decoded_payload_json': {
                    'operation_type': 'add_application_type',
                    'application_type': 'DeFi',
                    'application_id': 'app-ams',
                },
                'decode_error': None,
                'metadata_json': None,
                'decoder_version': 'ams-operation-rust-v1',
            },
        )

    def test_dispatch_decodes_real_ams_add_application_type_message(self):
        from registry.ams_message_decoder import AmsMessageDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-ams',
            app_type='ams',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='ams',
            payload_kind='message',
            decoder=AmsMessageDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-ams',
            payload_kind='message',
            raw_bytes=self.FIXTURES.load_bytes('ams_add_application_type_message'),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'add_application_type')
        self.assertEqual(result.to_dict()['decoder_version'], 'ams-message-rust-v1')
        self.assertEqual(
            result.to_dict()['decoded_payload_json']['application_type'],
            'DeFi',
        )

    def test_dispatch_decodes_real_swap_update_pool_operation(self):
        from registry.swap_operation_decoder import SwapOperationDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-swap',
            app_type='swap',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='swap',
            payload_kind='operation',
            decoder=SwapOperationDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-swap',
            payload_kind='operation',
            raw_bytes=self.FIXTURES.load_bytes('swap_update_pool_operation'),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'update_pool')
        self.assertEqual(result.to_dict()['decoder_version'], 'swap-operation-rust-v1')
        self.assertEqual(
            result.to_dict()['decoded_payload_json']['transaction']['transaction_type'],
            'AddLiquidity',
        )

    def test_dispatch_decodes_real_swap_update_pool_message(self):
        from registry.swap_message_decoder import SwapMessageDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-swap',
            app_type='swap',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='swap',
            payload_kind='message',
            decoder=SwapMessageDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-swap',
            payload_kind='message',
            raw_bytes=self.FIXTURES.load_bytes('swap_update_pool_message'),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'update_pool')
        self.assertEqual(result.to_dict()['decoder_version'], 'swap-message-rust-v1')
        self.assertEqual(
            result.to_dict()['decoded_payload_json']['transaction']['transaction_id'],
            12,
        )

    def test_dispatch_decodes_real_meme_transfer_operation(self):
        from registry.meme_operation_decoder import MemeOperationDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-meme',
            app_type='meme',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='meme',
            payload_kind='operation',
            decoder=MemeOperationDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-meme',
            payload_kind='operation',
            raw_bytes=self.FIXTURES.load_bytes('meme_transfer_operation'),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'transfer')
        self.assertEqual(result.to_dict()['decoder_version'], 'meme-operation-rust-v1')
        self.assertEqual(result.to_dict()['decoded_payload_json']['amount'], '13')

    def test_dispatch_decodes_real_meme_transfer_message(self):
        from registry.meme_message_decoder import MemeMessageDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-meme',
            app_type='meme',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='meme',
            payload_kind='message',
            decoder=MemeMessageDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-meme',
            payload_kind='message',
            raw_bytes=self.FIXTURES.load_bytes('meme_transfer_message'),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'transfer')
        self.assertEqual(result.to_dict()['decoder_version'], 'meme-message-rust-v1')
        self.assertEqual(result.to_dict()['decoded_payload_json']['amount'], '13')

    def test_dispatch_decodes_real_pool_swap_operation(self):
        from registry.pool_operation_decoder import PoolOperationDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='pool',
            payload_kind='operation',
            decoder=PoolOperationDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-pool',
            payload_kind='operation',
            raw_bytes=(
                bytes([4, 1])
                + (5).to_bytes(16, 'little')
                + bytes([0, 1])
                + (7).to_bytes(16, 'little')
                + bytes([0, 0, 0])
            ),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'swap')
        self.assertEqual(result.to_dict()['decoder_version'], 'pool-operation-rust-v1')

    def test_dispatch_decodes_real_proxy_register_miner_message(self):
        from registry.proxy_message_decoder import ProxyMessageDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-proxy',
            app_type='proxy',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='proxy',
            payload_kind='message',
            decoder=ProxyMessageDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-proxy',
            payload_kind='message',
            raw_bytes=self.FIXTURES.load_bytes('proxy_register_miner_message'),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'register_miner')
        self.assertEqual(result.to_dict()['decoder_version'], 'proxy-message-rust-v1')
        self.assertEqual(
            result.to_dict()['decoded_payload_json']['owner']['chain_id'],
            '11' * 32,
        )

    def test_dispatch_decodes_real_blob_gateway_register_message(self):
        from registry.blob_gateway_message_decoder import BlobGatewayMessageDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-blob',
            app_type='blob-gateway',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='blob-gateway',
            payload_kind='message',
            decoder=BlobGatewayMessageDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-blob',
            payload_kind='message',
            raw_bytes=self.FIXTURES.load_bytes('blob_gateway_register_message'),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'blob_gateway_register')
        self.assertEqual(result.to_dict()['decoder_version'], 'blob-gateway-message-rust-v1')
        self.assertEqual(
            result.to_dict()['decoded_payload_json']['blob_hash_hex'],
            '22' * 32,
        )

    def test_dispatch_decodes_legacy_pool_new_transaction_history_message(self):
        from registry.pool_message_decoder import PoolMessageDecoder

        repository = self.FakeRepository()
        registry = ApplicationRegistry(repository)
        registry.register_known_application(
            application_id='app-pool',
            app_type='pool',
        )
        decoder_registry = DecoderRegistry()
        decoder_registry.register(
            app_type='pool',
            payload_kind='message',
            decoder=PoolMessageDecoder(),
        )
        dispatcher = DecoderDispatcher(
            application_registry=registry,
            decoder_registry=decoder_registry,
        )

        result = dispatcher.dispatch(
            application_id='app-pool',
            payload_kind='message',
            raw_bytes=b''.join([
                bytes([8]),
                bytes([1]),
                (12).to_bytes(4, 'little'),
                bytes([2]),
                bytes.fromhex('11' * 32),
                bytes([1]),
                bytes.fromhex('22' * 32),
                bytes([1]),
                (3).to_bytes(16, 'little'),
                bytes([0]),
                bytes([1]),
                (4).to_bytes(16, 'little'),
                bytes([0]),
                bytes([1]),
                (5).to_bytes(16, 'little'),
                (99).to_bytes(8, 'little'),
            ]),
        )

        self.assertEqual(result.to_dict()['payload_type'], 'new_transaction')
        self.assertEqual(result.to_dict()['decoder_version'], 'pool-message-rust-v1')
        self.assertEqual(
            result.to_dict()['decoded_payload_json']['message_type'],
            'new_transaction',
        )
        self.assertEqual(
            result.to_dict()['decoded_payload_json']['transaction']['transaction_type'],
            'AddLiquidity',
        )
