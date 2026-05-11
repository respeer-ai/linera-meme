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

from subscription import KlineSubscription, PositionsSubscription, WebSocketManager  # noqa: E402


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


class FakePoolCatalogRepository:
    def __init__(self, pools):
        self.pools = pools

    def list_current_pool_views(self):
        return list(self.pools)


class FakeCandleReader:
    def __init__(self):
        self.calls = []

    def get_last_points(self, **kwargs):
        self.calls.append(kwargs)
        return {
            'pool_id': kwargs.get('pool_id'),
            'pool_application': kwargs.get('pool_application'),
            'token_0': kwargs['token_0'],
            'token_1': kwargs['token_1'],
            'interval': kwargs['interval'],
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
        }


class SubscriptionManagerTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        pools = [
            types.SimpleNamespace(
                token_0='AAA',
                token_1='BBB',
                pool_id=1001,
                pool_application=types.SimpleNamespace(chain_id='chain-a', owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),
            ),
            types.SimpleNamespace(
                token_0='CCC',
                token_1='DDD',
                pool_id=1002,
                pool_application=types.SimpleNamespace(chain_id='chain-b', owner='0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb'),
            ),
        ]
        self.candle_reader = FakeCandleReader()
        self.manager = WebSocketManager(
            FakeSwap(pools),
            self.candle_reader,
            FakePoolCatalogRepository(pools),
        )

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

    def test_handle_message_tracks_positions_subscription(self):
        websocket = FakeWebSocket()
        self.manager.positions_subscriptions[websocket] = set()

        self.manager.handle_message(websocket, {
            'action': 'subscribe',
            'topic': 'positions',
            'owner': 'owner-a',
            'pool_id': 7,
            'pool_application': 'pool-app',
        })

        self.assertEqual(
            self.manager.positions_subscriptions[websocket],
            {PositionsSubscription(owner='owner-a', pool_id=7, pool_application='pool-app')},
        )

    async def test_notify_kline_only_sends_requested_pair_and_interval_for_subscribed_connection(self):
        websocket = FakeWebSocket()
        self.manager.connections = [websocket]
        self.manager.kline_subscriptions[websocket] = {
            KlineSubscription(token_0='AAA', token_1='BBB', interval='5min'),
        }

        await self.manager.notify_kline()

        self.assertEqual(self.candle_reader.calls, [{
            'token_0': 'AAA',
            'token_1': 'BBB',
            'interval': '5min',
            'pool_id': None,
            'pool_application': None,
        }])
        self.assertEqual(websocket.sent, [{
            'notification': 'kline',
            'value': {
                '5min': [{
                    'pool_id': None,
                    'pool_application': None,
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

    async def test_notify_kline_requires_projection_pool_catalog_for_broadcast(self):
        pools = [
            types.SimpleNamespace(
                token_0='AAA',
                token_1='BBB',
                pool_id=1001,
                pool_application=types.SimpleNamespace(chain_id='chain-a', owner='0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'),
            ),
        ]
        manager = WebSocketManager(FakeSwap(pools), self.candle_reader, None)
        websocket = FakeWebSocket()
        manager.connections = [websocket]
        manager.kline_subscriptions[websocket] = set()

        with self.assertRaisesRegex(
            RuntimeError,
            'Projection pool catalog repository is required',
        ):
            await manager.notify_kline()

    async def test_notify_kline_preserves_legacy_broadcast_for_unsubscribed_connection(self):
        websocket = FakeWebSocket()
        self.manager.connections = [websocket]
        self.manager.kline_subscriptions[websocket] = set()

        await self.manager.notify_kline()

        self.assertIn({
            'token_0': 'AAA',
            'token_1': 'BBB',
            'interval': '1min',
            'pool_id': 1001,
            'pool_application': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
        }, self.candle_reader.calls)
        self.assertIn({
            'token_0': 'BBB',
            'token_1': 'AAA',
            'interval': '1min',
            'pool_id': 1001,
            'pool_application': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
        }, self.candle_reader.calls)
        self.assertIn({
            'token_0': 'CCC',
            'token_1': 'DDD',
            'interval': '1ME',
            'pool_id': 1002,
            'pool_application': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-b',
        }, self.candle_reader.calls)
        self.assertEqual(websocket.sent[0]['notification'], 'kline')
        self.assertIn('1min', websocket.sent[0]['value'])
        self.assertIn('1d', websocket.sent[0]['value'])
        self.assertIn('1w', websocket.sent[0]['value'])
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

        self.assertEqual(self.candle_reader.calls, [])
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

        self.assertEqual(self.candle_reader.calls, [])
        self.assertEqual(websocket.sent, [{
            'notification': 'kline',
            'value': payload,
        }])

    async def test_notify_positions_filters_by_owner_pool_and_application(self):
        websocket = FakeWebSocket()
        self.manager.connections = [websocket]
        self.manager.positions_subscriptions[websocket] = {
            PositionsSubscription(owner='owner-a', pool_id=7, pool_application='pool-app'),
        }

        await self.manager.notify_positions({
            'events': [
                {
                    'owners': ['owner-a'],
                    'pool_id': 7,
                    'pool_application': 'pool-app',
                    'event_types': ['settled_liquidity_change'],
                },
                {
                    'owners': ['owner-b'],
                    'pool_id': 8,
                    'pool_application': 'other-pool',
                    'event_types': ['settled_liquidity_change'],
                },
            ],
        })

        self.assertEqual(websocket.sent, [{
            'notification': 'positions',
            'value': {
                'events': [{
                    'owners': ['owner-a'],
                    'pool_id': 7,
                    'pool_application': 'pool-app',
                    'event_types': ['settled_liquidity_change'],
                }],
            },
        }])

    async def test_notify_positions_treats_empty_owners_as_pool_wide_invalidation(self):
        websocket = FakeWebSocket()
        self.manager.connections = [websocket]
        self.manager.positions_subscriptions[websocket] = {
            PositionsSubscription(owner='owner-a', pool_id=7, pool_application='pool-app'),
        }

        await self.manager.notify_positions({
            'events': [
                {
                    'owners': [],
                    'pool_id': 7,
                    'pool_application': 'pool-app',
                    'event_types': ['settled_trade'],
                },
            ],
        })

        self.assertEqual(websocket.sent, [{
            'notification': 'positions',
            'value': {
                'events': [{
                    'owners': [],
                    'pool_id': 7,
                    'pool_application': 'pool-app',
                    'event_types': ['settled_trade'],
                }],
            },
        }])


if __name__ == '__main__':
    unittest.main()
