import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.pool_executed_event_payload import PoolExecutedEventPayload  # noqa: E402


class PoolExecutedEventPayloadTest(unittest.TestCase):
    def test_from_event_returns_none_for_non_executed_family(self):
        payload = PoolExecutedEventPayload.from_event(
            {
                'event_family': 'pool_swap_message_observed',
                'event_payload_json': {'decoded_payload_json': {'execution': {}}},
            }
        )

        self.assertIsNone(payload)

    def test_from_event_returns_none_when_execution_payload_is_missing(self):
        payload = PoolExecutedEventPayload.from_event(
            {
                'event_family': 'pool_swap_executed',
                'event_payload_json': {'decoded_payload_json': {}},
            }
        )

        self.assertIsNone(payload)

    def test_from_event_builds_trade_payload(self):
        payload = PoolExecutedEventPayload.from_event(
            {
                'event_family': 'pool_swap_executed',
                'event_payload_json': {
                    'decoded_payload_json': {
                        'execution': {
                            'transaction_id': 19,
                            'trade_type': 'buy_token_0',
                            'from': {'chain_id': 'user-chain', 'owner': 'user-owner'},
                            'amount_0_out': '300',
                            'amount_1_in': '25',
                            'executed_at_micros': 1234567000,
                        }
                    }
                },
            }
        )

        self.assertIsNotNone(payload)
        self.assertTrue(payload.is_trade())
        self.assertFalse(payload.is_liquidity())
        self.assertEqual(payload.trade_type(), 'buy_token_0')
        self.assertEqual(payload.amount_0_out(), '300')
        self.assertEqual(payload.amount_1_in(), '25')
        self.assertEqual(payload.transaction_id(), 19)

    def test_from_event_builds_liquidity_payload(self):
        payload = PoolExecutedEventPayload.from_event(
            {
                'event_family': 'pool_add_liquidity_executed',
                'event_payload_json': {
                    'decoded_payload_json': {
                        'execution': {
                            'transaction_id': 20,
                            'change_type': 'add_liquidity',
                            'from': {'chain_id': 'user-chain', 'owner': 'user-owner'},
                            'amount_0_in': '1000',
                            'amount_1_in': '55',
                            'liquidity': '888',
                            'executed_at_micros': 555000,
                        }
                    }
                },
            }
        )

        self.assertIsNotNone(payload)
        self.assertFalse(payload.is_trade())
        self.assertTrue(payload.is_liquidity())
        self.assertEqual(payload.change_type(), 'add_liquidity')
        self.assertEqual(payload.amount_0_in(), '1000')
        self.assertEqual(payload.amount_1_in(), '55')
        self.assertEqual(payload.liquidity(), '888')


if __name__ == '__main__':
    unittest.main()
