import asyncio
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from integration.linera_graphql_notification_listener import LineraGraphqlNotificationListener  # noqa: E402


class LineraGraphqlNotificationListenerTest(unittest.IsolatedAsyncioTestCase):
    class FakeChainEventProcessor:
        def __init__(self):
            self.notifications = []
            self.reconnects = []

        async def on_chain_notification(self, chain_id: str) -> dict:
            self.notifications.append(chain_id)
            return {'chain_id': chain_id}

        async def on_subscription_reconnect(self, chain_id: str) -> dict:
            self.reconnects.append(chain_id)
            return {'chain_id': chain_id}

    class FakeWebSocket:
        def __init__(self, incoming_messages):
            self.incoming_messages = list(incoming_messages)
            self.sent_messages = []
            self.blocker = asyncio.Event()

        async def send(self, message):
            self.sent_messages.append(json.loads(message))

        async def recv(self):
            if self.incoming_messages:
                item = self.incoming_messages.pop(0)
                if isinstance(item, Exception):
                    raise item
                if isinstance(item, dict):
                    return json.dumps(item)
                return item
            await self.blocker.wait()
            return json.dumps({'type': 'complete'})

    class FakeWebSocketConnection:
        def __init__(self, websocket):
            self.websocket = websocket

        async def __aenter__(self):
            return self.websocket

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class FakeConnector:
        def __init__(self, websockets):
            self.websockets = list(websockets)
            self.calls = []

        def __call__(self, url, subprotocols=None):
            self.calls.append((url, tuple(subprotocols or ())))
            if not self.websockets:
                raise RuntimeError('no websocket prepared')
            return LineraGraphqlNotificationListenerTest.FakeWebSocketConnection(
                self.websockets.pop(0)
            )

    async def test_listener_subscribes_and_dispatches_notifications(self):
        processor = self.FakeChainEventProcessor()
        websocket = self.FakeWebSocket(
            [
                {'type': 'connection_ack'},
                {
                    'id': 'chain-a',
                    'type': 'next',
                    'payload': {
                        'data': {
                            'notifications': {
                                'chain_id': 'chain-a',
                                'reason': {'NewBlock': {'height': '1', 'hash': 'abc'}},
                            }
                        }
                    },
                },
            ]
        )
        connector = self.FakeConnector([websocket])
        listener = LineraGraphqlNotificationListener(
            graphql_url='https://linera.example',
            chain_ids=('chain-a',),
            chain_event_processor=processor,
            websocket_connect=connector,
        )

        await listener.start()
        await self._wait_for(lambda: processor.notifications == ['chain-a'])
        await listener.stop()

        self.assertEqual(connector.calls, [('wss://linera.example/ws', ('graphql-transport-ws',))])
        self.assertEqual(websocket.sent_messages[0]['type'], 'connection_init')
        self.assertEqual(websocket.sent_messages[1]['type'], 'subscribe')
        self.assertEqual(websocket.sent_messages[1]['payload']['variables'], {'chainId': 'chain-a'})

    async def test_listener_triggers_reconnect_reconciliation_after_disconnect(self):
        processor = self.FakeChainEventProcessor()
        first_socket = self.FakeWebSocket(
            [
                {'type': 'connection_ack'},
                RuntimeError('connection dropped'),
            ]
        )
        second_socket = self.FakeWebSocket(
            [
                {'type': 'connection_ack'},
                {
                    'id': 'chain-a',
                    'type': 'next',
                    'payload': {'data': {'notifications': 'opaque-notification'}},
                },
            ]
        )
        connector = self.FakeConnector([first_socket, second_socket])
        sleep_calls = []

        async def fake_sleep(seconds):
            sleep_calls.append(seconds)
            await asyncio.sleep(0)

        listener = LineraGraphqlNotificationListener(
            graphql_url='https://linera.example',
            chain_ids=('chain-a',),
            chain_event_processor=processor,
            websocket_connect=connector,
            sleep_func=fake_sleep,
        )

        await listener.start()
        await self._wait_for(
            lambda: processor.reconnects == ['chain-a'] and processor.notifications == ['chain-a']
        )
        await listener.stop()

        self.assertEqual(sleep_calls, [1.0])
        self.assertEqual(len(connector.calls), 2)

    async def _wait_for(self, predicate, timeout: float = 1.0):
        deadline = asyncio.get_running_loop().time() + timeout
        while asyncio.get_running_loop().time() < deadline:
            if predicate():
                return
            await asyncio.sleep(0.01)
        self.fail('condition not met before timeout')
