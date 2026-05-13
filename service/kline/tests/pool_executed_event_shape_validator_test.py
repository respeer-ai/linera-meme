import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from normalizer.pool_executed_event_shape_validator import PoolExecutedEventShapeValidator  # noqa: E402


class PoolExecutedEventShapeValidatorTest(unittest.TestCase):
    def test_ignores_non_pool_event_results(self):
        validator = PoolExecutedEventShapeValidator()

        self.assertIsNone(validator.validate({
            'app_type': 'pool',
            'payload_kind': 'message',
            'payload_type': 'swap',
        }))
        self.assertIsNone(validator.validate({
            'app_type': 'swap',
            'payload_kind': 'event',
            'payload_type': 'swap_executed',
        }))

    def test_accepts_valid_trade_execution_shape(self):
        validator = PoolExecutedEventShapeValidator()

        self.assertIsNone(validator.validate({
            'app_type': 'pool',
            'payload_kind': 'event',
            'payload_type': 'swap_executed',
            'decoded_payload_json': {
                'execution': {
                    'transaction_id': 1,
                    'executed_at_micros': 2,
                    'from': {'chain_id': 'c', 'owner': 'o'},
                    'trade_type': 'buy_token_0',
                    'amount_1_in': '3',
                    'amount_0_out': '4',
                },
            },
        }))

    def test_rejects_trade_execution_with_missing_fields(self):
        validator = PoolExecutedEventShapeValidator()

        error = validator.validate({
            'app_type': 'pool',
            'payload_kind': 'event',
            'payload_type': 'swap_executed',
            'decoded_payload_json': {
                'execution': {
                    'transaction_id': 1,
                    'executed_at_micros': 2,
                    'from': {'chain_id': 'c', 'owner': 'o'},
                    'trade_type': 'buy_token_0',
                    'amount_1_in': '3',
                },
            },
        })

        self.assertEqual(error, 'buy execution.amount_0_out is required')

    def test_accepts_valid_liquidity_execution_shape(self):
        validator = PoolExecutedEventShapeValidator()

        self.assertIsNone(validator.validate({
            'app_type': 'pool',
            'payload_kind': 'event',
            'payload_type': 'add_liquidity_executed',
            'decoded_payload_json': {
                'execution': {
                    'transaction_id': 1,
                    'executed_at_micros': 2,
                    'from': {'chain_id': 'c', 'owner': 'o'},
                    'change_type': 'add_liquidity',
                    'amount_0_in': '3',
                    'amount_1_in': '4',
                    'liquidity': '5',
                },
            },
        }))

    def test_rejects_liquidity_execution_with_missing_fields(self):
        validator = PoolExecutedEventShapeValidator()

        error = validator.validate({
            'app_type': 'pool',
            'payload_kind': 'event',
            'payload_type': 'remove_liquidity_executed',
            'decoded_payload_json': {
                'execution': {
                    'transaction_id': 1,
                    'executed_at_micros': 2,
                    'from': {'chain_id': 'c', 'owner': 'o'},
                    'change_type': 'remove_liquidity',
                    'amount_0_out': '3',
                    'liquidity': '5',
                },
            },
        })

        self.assertEqual(error, 'remove execution.amount_1_out is required')


if __name__ == '__main__':
    unittest.main()
