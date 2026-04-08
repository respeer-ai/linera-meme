import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


fastapi_stub = types.ModuleType('fastapi')
fastapi_stub.WebSocket = object
sys.modules.setdefault('fastapi', fastapi_stub)

from subscription import KlineSubscription, WebSocketManager  # noqa: E402


class FakeWebSocket:
    def __init__(self, client='127.0.0.1'):
        self.scope = {'client': client}
        self.sent = []

    async def send_json(self, payload):
        self.sent.append(payload)


class FakeSwap:
    def __init__(self, pools):
        self.pools = pools

    async def get_pools(self):
        return self.pools


class FakeDb:
    def __init__(self):
        self.calls = []

    def get_last_kline(self, token_0, token_1, interval):
        self.calls.append((token_0, token_1, interval))
        return (
            token_0,
            token_1,
            1_000,
            2_000,
            interval,
            [{
                'timestamp': 1_000,
                'open': 1.0,
                'high': 1.0,
                'low': 1.0,
                'close': 1.0,
                'base_volume': 1.0,
                'quote_volume': 2.0,
            }],
        )


class SubscriptionManagerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        pools = [
            types.SimpleNamespace(token_0='AAA', token_1='BBB'),
            types.SimpleNamespace(token_0='CCC', token_1='DDD'),
        ]
        self.db = FakeDb()
        self.manager = WebSocketManager(FakeSwap(pools), self.db)

    def test_handle_message_tracks_pair_aware_interval_aware_subscription(self):
        websocket = FakeWebSocket()
        self.manager.kline_subscriptions[websocket] = set()

        self.manager.handle_message(websocket, {
            'action': 'subscribe',
            'topic': 'kline',
            'token_0': 'AAA',
            'token_1': 'BBB',
            'intervals': ['1min', '5min'],
        })

        self.assertEqual(
            self.manager.kline_subscriptions[websocket],
            {
                KlineSubscription(token_0='AAA', token_1='BBB', interval='1min'),
                KlineSubscription(token_0='AAA', token_1='BBB', interval='5min'),
            },
        )

    async def test_notify_kline_only_sends_requested_pair_and_interval_for_subscribed_connection(self):
        websocket = FakeWebSocket()
        self.manager.connections = [websocket]
        self.manager.kline_subscriptions[websocket] = {
            KlineSubscription(token_0='AAA', token_1='BBB', interval='5min'),
        }

        await self.manager.notify_kline()

        self.assertEqual(self.db.calls, [('AAA', 'BBB', '5min')])
        self.assertEqual(websocket.sent, [{
            'notification': 'kline',
            'value': {
                '5min': [{
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'interval': '5min',
                    'start_at': 1_000,
                    'end_at': 2_000,
                    'points': [{
                        'timestamp': 1_000,
                        'open': 1.0,
                        'high': 1.0,
                        'low': 1.0,
                        'close': 1.0,
                        'base_volume': 1.0,
                        'quote_volume': 2.0,
                    }],
                }],
            },
        }])

    async def test_notify_kline_preserves_legacy_broadcast_for_unsubscribed_connection(self):
        websocket = FakeWebSocket()
        self.manager.connections = [websocket]
        self.manager.kline_subscriptions[websocket] = set()

        await self.manager.notify_kline()

        self.assertIn(('AAA', 'BBB', '1min'), self.db.calls)
        self.assertIn(('BBB', 'AAA', '1min'), self.db.calls)
        self.assertIn(('CCC', 'DDD', '1ME'), self.db.calls)
        self.assertEqual(websocket.sent[0]['notification'], 'kline')
        self.assertIn('1min', websocket.sent[0]['value'])
        self.assertIn('1ME', websocket.sent[0]['value'])

    async def test_notify_kline_filters_incremental_payload_for_subscribed_connection(self):
        websocket = FakeWebSocket()
        self.manager.connections = [websocket]
        self.manager.kline_subscriptions[websocket] = {
            KlineSubscription(token_0='AAA', token_1='BBB', interval='5min'),
        }

        await self.manager.notify_kline({
            '5min': [
                {
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'interval': '5min',
                    'start_at': 1_000,
                    'end_at': 2_000,
                    'points': [{
                        'timestamp': 1_000,
                        'open': 1.0,
                        'high': 1.0,
                        'low': 1.0,
                        'close': 1.0,
                        'base_volume': 1.0,
                        'quote_volume': 2.0,
                    }],
                },
                {
                    'token_0': 'CCC',
                    'token_1': 'DDD',
                    'interval': '5min',
                    'start_at': 1_000,
                    'end_at': 2_000,
                    'points': [{
                        'timestamp': 1_000,
                        'open': 2.0,
                        'high': 2.0,
                        'low': 2.0,
                        'close': 2.0,
                        'base_volume': 2.0,
                        'quote_volume': 4.0,
                    }],
                },
            ],
            '1min': [
                {
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'interval': '1min',
                    'start_at': 1_000,
                    'end_at': 2_000,
                    'points': [{
                        'timestamp': 1_000,
                        'open': 3.0,
                        'high': 3.0,
                        'low': 3.0,
                        'close': 3.0,
                        'base_volume': 3.0,
                        'quote_volume': 6.0,
                    }],
                },
            ],
        })

        self.assertEqual(self.db.calls, [])
        self.assertEqual(websocket.sent, [{
            'notification': 'kline',
            'value': {
                '5min': [{
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'interval': '5min',
                    'start_at': 1_000,
                    'end_at': 2_000,
                    'points': [{
                        'timestamp': 1_000,
                        'open': 1.0,
                        'high': 1.0,
                        'low': 1.0,
                        'close': 1.0,
                        'base_volume': 1.0,
                        'quote_volume': 2.0,
                    }],
                }],
            },
        }])

    async def test_notify_kline_sends_incremental_payload_to_unsubscribed_connection_without_pool_scan(self):
        websocket = FakeWebSocket()
        self.manager.connections = [websocket]
        self.manager.kline_subscriptions[websocket] = set()

        payload = {
            '5min': [
                {
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'interval': '5min',
                    'start_at': 1_000,
                    'end_at': 2_000,
                    'points': [{
                        'timestamp': 1_000,
                        'open': 1.0,
                        'high': 1.0,
                        'low': 1.0,
                        'close': 1.0,
                        'base_volume': 1.0,
                        'quote_volume': 2.0,
                    }],
                },
            ],
        }

        await self.manager.notify_kline(payload)

        self.assertEqual(self.db.calls, [])
        self.assertEqual(websocket.sent, [{
            'notification': 'kline',
            'value': payload,
        }])


if __name__ == '__main__':
    unittest.main()
