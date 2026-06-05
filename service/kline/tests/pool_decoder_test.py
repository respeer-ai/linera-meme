import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from registry.pool_message_decoder import PoolMessageDecoder  # noqa: E402
from registry.pool_operation_decoder import PoolOperationDecoder  # noqa: E402
from rust_fixture_loader import RustFixtureLoader  # noqa: E402


class PoolDecoderTest(unittest.TestCase):
    FIXTURES = RustFixtureLoader()

    def test_pool_operation_decoder_reads_swap_variant(self):
        decoder = PoolOperationDecoder()

        decoded = decoder.decode(
            raw_bytes=self.FIXTURES.load_bytes('pool_swap_operation'),
            application={'application_id': 'app-pool'},
            payload_kind='operation',
        )

        self.assertEqual(decoded['payload_type'], 'swap')
        self.assertEqual(decoded['decoded_payload_json']['operation_type'], 'swap')
        self.assertEqual(decoded['decoded_payload_json']['amount_0_in'], '5')
        self.assertIsNone(decoded['decoded_payload_json']['amount_0_out_min'])
        self.assertEqual(decoded['decoded_payload_json']['amount_1_out_min'], '7')
        self.assertIsNone(decoded['decoded_payload_json']['amount_1_in'])

    def test_pool_message_decoder_reads_fund_result_variant(self):
        decoder = PoolMessageDecoder()

        decoded = decoder.decode(
            raw_bytes=self.FIXTURES.load_bytes('pool_fund_result_message'),
            application={'application_id': 'app-pool'},
            payload_kind='message',
        )

        self.assertEqual(decoded['payload_type'], 'fund_result')
        payload = decoded['decoded_payload_json']
        self.assertEqual(payload['message_type'], 'fund_result')
        self.assertEqual(payload['request']['amount_in'], '13')
        self.assertEqual(payload['request']['fund_type'], 'Swap')
        self.assertTrue(payload['result']['ok'])

    def test_pool_message_decoder_reads_claim_transfer_receipt_variant(self):
        decoder = PoolMessageDecoder()

        decoded = decoder.decode(
            raw_bytes=self.FIXTURES.load_bytes('pool_claim_transfer_receipt_message'),
            application={'application_id': 'app-pool'},
            payload_kind='message',
        )

        self.assertEqual(decoded['payload_type'], 'claim_transfer_receipt')
        payload = decoded['decoded_payload_json']
        self.assertEqual(payload['message_type'], 'claim_transfer_receipt')
        self.assertEqual(payload['receipt']['amount'], '13')
        self.assertTrue(payload['receipt']['result']['ok'])

    def test_pool_message_decoder_reads_new_transaction_message(self):
        decoder = PoolMessageDecoder()

        decoded = decoder.decode(
            raw_bytes=self.FIXTURES.load_bytes('pool_new_transaction_message'),
            application={'application_id': 'app-pool'},
            payload_kind='message',
        )

        self.assertEqual(decoded['payload_type'], 'new_transaction')
        self.assertEqual(decoded['decoded_payload_json']['message_type'], 'new_transaction')
        transaction = decoded['decoded_payload_json']['transaction']
        self.assertEqual(transaction['transaction_id'], 12)
        self.assertEqual(transaction['transaction_type'], 'AddLiquidity')
        self.assertEqual(transaction['from']['chain_id'], '33' * 32)
        self.assertEqual(transaction['from']['owner'], '0x' + '44' * 32)
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
