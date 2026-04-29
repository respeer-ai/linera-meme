import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from registry.pool_message_decoder import PoolMessageDecoder  # noqa: E402
from registry.pool_operation_decoder import PoolOperationDecoder  # noqa: E402


class PoolDecoderTest(unittest.TestCase):
    def test_pool_operation_decoder_reads_swap_variant(self):
        decoder = PoolOperationDecoder()

        decoded = decoder.decode(
            raw_bytes=bytes([4, 1]) + (5).to_bytes(16, 'little') + bytes([0, 1]) + (7).to_bytes(16, 'little') + bytes([0, 0, 0]),
            application={'application_id': 'app-pool'},
            payload_kind='operation',
        )

        self.assertEqual(decoded['payload_type'], 'swap')
        self.assertEqual(decoded['decoded_payload_json']['operation_type'], 'swap')
        self.assertEqual(decoded['decoded_payload_json']['amount_0_in'], '5')
        self.assertEqual(decoded['decoded_payload_json']['amount_0_out_min'], '7')
        self.assertIsNone(decoded['decoded_payload_json']['amount_1_in'])

    def test_pool_message_decoder_reads_fund_success_variant(self):
        decoder = PoolMessageDecoder()

        decoded = decoder.decode(
            raw_bytes=bytes([1]) + (9).to_bytes(8, 'little'),
            application={'application_id': 'app-pool'},
            payload_kind='message',
        )

        self.assertEqual(decoded['payload_type'], 'fund_success')
        self.assertEqual(decoded['decoded_payload_json']['message_type'], 'fund_success')
        self.assertEqual(decoded['decoded_payload_json']['transfer_id'], 9)

    def test_pool_message_decoder_reads_new_transaction_fields(self):
        decoder = PoolMessageDecoder()
        raw_bytes = b''.join([
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
        ])

        decoded = decoder.decode(
            raw_bytes=raw_bytes,
            application={'application_id': 'app-pool'},
            payload_kind='message',
        )

        self.assertEqual(decoded['payload_type'], 'new_transaction')
        transaction = decoded['decoded_payload_json']['transaction']
        self.assertEqual(transaction['transaction_id'], 12)
        self.assertEqual(transaction['transaction_type'], 'add_liquidity')
        self.assertEqual(transaction['from']['chain_id'], '11' * 32)
        self.assertEqual(transaction['from']['owner'], '22' * 32)
        self.assertEqual(transaction['amount_0_in'], '3')
        self.assertEqual(transaction['amount_1_in'], '4')
        self.assertEqual(transaction['liquidity'], '5')
        self.assertEqual(transaction['created_at_micros'], 99)

    def test_pool_message_decoder_rejects_unknown_variant(self):
        decoder = PoolMessageDecoder()

        with self.assertRaisesRegex(ValueError, 'unsupported pool message variant'):
            decoder.decode(
                raw_bytes=bytes([42]),
                application={'application_id': 'app-pool'},
                payload_kind='message',
            )
