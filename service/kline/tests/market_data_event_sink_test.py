import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from realtime.market_data_event import MarketDataEvent  # noqa: E402
from realtime.market_data_event_sink import MarketDataEventSink  # noqa: E402


class FakeQueue:
    def __init__(self):
        self.events = []

    def put_nowait(self, event):
        self.events.append(event)


class MarketDataEventSinkTest(unittest.TestCase):
    def test_publishes_settled_trade_and_liquidity_change_after_derivation_batch(self):
        queue = FakeQueue()
        sink = MarketDataEventSink(queue, now_ms=lambda: 1_800_000_000_000)

        sink.publish_derivation_batch([
            {
                'settled_outputs': [
                    {
                        'settled_output_type': 'settled_trade',
                        'pool_application_id': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                        'pool_chain_id': 'chain-a',
                        'side': 'sell_token_0',
                        'transaction_id': '10',
                        'trade_time_ms': '1770000000000',
                    },
                    {
                        'settled_output_type': 'settled_liquidity_change',
                        'pool_application_id': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
                        'pool_chain_id': 'chain-b',
                        'owner': '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc@chain-c',
                        'transaction_id': '11',
                        'event_time_ms': '1770000000100',
                    },
                ],
            },
        ])

        self.assertEqual(len(queue.events), 2)
        self.assertEqual(queue.events[0].event_type, MarketDataEvent.TYPE_SETTLED_TRADE)
        self.assertEqual(queue.events[0].token_reversed, True)
        self.assertEqual(queue.events[0].pool_application, '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a')
        self.assertEqual(queue.events[1].event_type, MarketDataEvent.TYPE_SETTLED_LIQUIDITY_CHANGE)
        self.assertEqual(queue.events[1].owner, '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc@chain-c')


if __name__ == '__main__':
    unittest.main()
