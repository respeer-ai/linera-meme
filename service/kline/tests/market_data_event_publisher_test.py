import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from realtime.market_data_event import MarketDataEvent  # noqa: E402
from realtime.market_data_event_publisher import MarketDataEventPublisher  # noqa: E402


class FakeQueue:
    def drain_nowait(self):
        return []


class FakePayloadBuilder:
    def __init__(self, payload):
        self.payload = payload
        self.events = None

    def build(self, events):
        self.events = events
        return self.payload


class MarketDataEventPublisherTest(unittest.IsolatedAsyncioTestCase):
    async def test_publish_fans_out_non_empty_topics_only(self):
        manager = AsyncMock()
        builder = FakePayloadBuilder({
            'kline': {'1min': [{'points': []}]},
            'transactions': [{'transactions': []}],
            'positions': {'events': [{'owner': 'owner'}]},
        })
        publisher = MarketDataEventPublisher(
            queue=FakeQueue(),
            websocket_manager=manager,
            payload_builder=builder,
        )
        events = [MarketDataEvent(event_type=MarketDataEvent.TYPE_SETTLED_TRADE)]

        await publisher.publish(events)

        self.assertEqual(builder.events, events)
        self.assertEqual(manager.notify.await_args_list[0].args, ('kline', {'1min': [{'points': []}]}))
        self.assertEqual(manager.notify.await_args_list[1].args, ('transactions', [{'transactions': []}]))
        self.assertEqual(manager.notify.await_args_list[2].args, ('positions', {'events': [{'owner': 'owner'}]}))


if __name__ == '__main__':
    unittest.main()

