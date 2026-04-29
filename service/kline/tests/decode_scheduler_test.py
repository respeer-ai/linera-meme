import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from registry.application_registry import ApplicationRegistry  # noqa: E402
from registry.ams_operation_decoder import AmsOperationDecoder  # noqa: E402
from registry.decode_scheduler import DecodeScheduler  # noqa: E402
from registry.decoder_dispatcher import DecoderDispatcher  # noqa: E402
from registry.decoder_registry import DecoderRegistry  # noqa: E402


class DecodeSchedulerTest(unittest.TestCase):
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

    def test_decode_item_wraps_decoded_result_with_raw_identity(self):
        registry = ApplicationRegistry(self.FakeRepository())
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
        scheduler = DecodeScheduler(
            DecoderDispatcher(
                application_registry=registry,
                decoder_registry=decoder_registry,
            )
        )

        decoded = scheduler.decode_item(
            {
                'raw_fact_id': 'raw-1',
                'raw_table': 'raw_operations',
                'application_id': 'app-ams',
                'payload_kind': 'operation',
                'raw_bytes': bytes([2, 4]) + b'DeFi',
            },
            reprocess_reason='registry_updated',
        )

        self.assertEqual(decoded['raw_fact_id'], 'raw-1')
        self.assertEqual(decoded['raw_table'], 'raw_operations')
        self.assertEqual(decoded['reprocess_reason'], 'registry_updated')
        self.assertEqual(decoded['decode_result']['status'], 'decoded')
        self.assertEqual(decoded['decode_result']['payload_type'], 'add_application_type')

    def test_decode_batch_preserves_decode_failures(self):
        registry = ApplicationRegistry(self.FakeRepository())
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
        scheduler = DecodeScheduler(
            DecoderDispatcher(
                application_registry=registry,
                decoder_registry=decoder_registry,
            )
        )

        decoded = scheduler.decode_batch(
            [
                {
                    'raw_fact_id': 'raw-1',
                    'raw_table': 'raw_operations',
                    'application_id': 'app-ams',
                    'payload_kind': 'operation',
                    'raw_bytes': bytes([2, 4]) + b'DeFi',
                },
                {
                    'raw_fact_id': 'raw-2',
                    'raw_table': 'raw_operations',
                    'application_id': 'app-ams',
                    'payload_kind': 'operation',
                    'raw_bytes': bytes([2, 8]) + b'Bad',
                },
            ],
            reprocess_reason='decoder_upgraded',
        )

        self.assertEqual(len(decoded), 2)
        self.assertEqual(decoded[0]['decode_result']['status'], 'decoded')
        self.assertEqual(decoded[1]['decode_result']['status'], 'decode_failed')
        self.assertEqual(decoded[1]['reprocess_reason'], 'decoder_upgraded')

    def test_decode_item_rejects_invalid_contract_item(self):
        scheduler = DecodeScheduler(decoder_dispatcher=object())

        with self.assertRaisesRegex(ValueError, 'missing decode item keys'):
            scheduler.decode_item(
                {
                    'raw_fact_id': 'raw-1',
                    'raw_table': 'raw_operations',
                }
            )
