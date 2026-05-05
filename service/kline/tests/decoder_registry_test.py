import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from registry.decoder_registry import DecoderRegistry  # noqa: E402


class DecoderRegistryTest(unittest.TestCase):
    def test_register_and_resolve_decoder_by_app_type_and_payload_kind(self):
        registry = DecoderRegistry()
        decoder = object()

        registry.register(app_type='pool', payload_kind='message', decoder=decoder)

        self.assertIs(
            registry.resolve(app_type='pool', payload_kind='message'),
            decoder,
        )
        self.assertIsNone(registry.resolve(app_type='pool', payload_kind='operation'))

    def test_list_supported_pairs_marks_implemented_and_unimplemented(self):
        registry = DecoderRegistry(
            registrations=(
                {'app_type': 'pool', 'payload_kind': 'message', 'decoder': object()},
                {'app_type': 'swap', 'payload_kind': 'operation', 'decoder': None},
            )
        )

        self.assertEqual(
            registry.list_supported_pairs(),
            [
                {'app_type': 'pool', 'payload_kind': 'message', 'implemented': True},
                {'app_type': 'swap', 'payload_kind': 'operation', 'implemented': False},
            ],
        )

    def test_register_known_pairs_keeps_unimplemented_slots_explicit(self):
        registry = DecoderRegistry()

        registry.register_known_pairs(
            (
                ('pool', 'operation'),
                ('pool', 'message'),
                ('pool', 'event'),
            )
        )

        self.assertEqual(
            registry.list_supported_pairs(),
            [
                {'app_type': 'pool', 'payload_kind': 'event', 'implemented': False},
                {'app_type': 'pool', 'payload_kind': 'message', 'implemented': False},
                {'app_type': 'pool', 'payload_kind': 'operation', 'implemented': False},
            ],
        )

    def test_register_real_decoder_marks_pair_as_implemented(self):
        registry = DecoderRegistry()
        registry.register_known_pairs((('blob-gateway', 'operation'),))
        registry.register(
            app_type='blob-gateway',
            payload_kind='operation',
            decoder=object(),
        )

        self.assertEqual(
            registry.list_supported_pairs(),
            [
                {'app_type': 'blob-gateway', 'payload_kind': 'operation', 'implemented': True},
            ],
        )

    def test_register_real_decoder_marks_ams_pair_as_implemented(self):
        registry = DecoderRegistry()
        registry.register_known_pairs((('ams', 'operation'),))
        registry.register(
            app_type='ams',
            payload_kind='operation',
            decoder=object(),
        )

        self.assertEqual(
            registry.list_supported_pairs(),
            [
                {'app_type': 'ams', 'payload_kind': 'operation', 'implemented': True},
            ],
        )
