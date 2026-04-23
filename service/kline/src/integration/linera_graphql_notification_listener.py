import asyncio
import json
from urllib.parse import urlparse, urlunparse


class LineraGraphqlNotificationListener:
    """Consumes Linera GraphQL notifications and turns them into event-driven catch-up triggers."""

    def __init__(
        self,
        graphql_url: str,
        chain_ids: tuple[str, ...],
        chain_event_processor,
        websocket_url: str | None = None,
        reconnect_delay_seconds: float = 1.0,
        websocket_connect=None,
        sleep_func=None,
    ):
        self.graphql_url = graphql_url.rstrip('/')
        self.websocket_url = self._resolve_websocket_url(websocket_url)
        self.chain_ids = tuple(chain_ids)
        self.chain_event_processor = chain_event_processor
        self.reconnect_delay_seconds = float(reconnect_delay_seconds)
        self._websocket_connect = websocket_connect or self._load_websocket_connect()
        self._sleep = sleep_func or asyncio.sleep
        self._tasks: dict[str, asyncio.Task] = {}

    async def start(self) -> None:
        if self._tasks:
            return
        for chain_id in self.chain_ids:
            self._tasks[chain_id] = asyncio.create_task(
                self._listen_chain(chain_id),
                name=f'linera-notification-{chain_id}',
            )

    async def stop(self) -> None:
        tasks = list(self._tasks.values())
        self._tasks = {}
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def _load_websocket_connect(self):
        import websockets

        return websockets.connect

    def _resolve_websocket_url(self, websocket_url: str | None) -> str:
        if websocket_url:
            return websocket_url
        parsed = urlparse(self.graphql_url)
        scheme = parsed.scheme
        if scheme == 'https':
            scheme = 'wss'
        elif scheme == 'http':
            scheme = 'ws'
        path = parsed.path.rstrip('/')
        if not path or path == '/':
            path = '/ws'
        elif not path.endswith('/ws'):
            path = f'{path}/ws'
        return urlunparse(parsed._replace(scheme=scheme, path=path))

    async def _listen_chain(self, chain_id: str) -> None:
        has_connected_once = False
        while True:
            try:
                async with self._websocket_connect(
                    self.websocket_url,
                    subprotocols=['graphql-transport-ws'],
                ) as websocket:
                    await self._initialize_connection(websocket)
                    if has_connected_once:
                        await self.chain_event_processor.on_subscription_reconnect(chain_id)
                    await self._subscribe(websocket, chain_id)
                    has_connected_once = True
                    await self._consume_notifications(websocket, chain_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                await self._sleep(self.reconnect_delay_seconds)

    async def _initialize_connection(self, websocket) -> None:
        await websocket.send(json.dumps({'type': 'connection_init', 'payload': {}}))
        while True:
            message = self._parse_message(await websocket.recv())
            message_type = str(message.get('type') or '')
            if message_type == 'connection_ack':
                return
            if message_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))

    async def _subscribe(self, websocket, chain_id: str) -> None:
        await websocket.send(
            json.dumps(
                {
                    'id': chain_id,
                    'type': 'subscribe',
                    'payload': {
                        'query': self._subscription_query(),
                        'variables': {'chainId': chain_id},
                    },
                }
            )
        )

    async def _consume_notifications(self, websocket, subscribed_chain_id: str) -> None:
        while True:
            message = self._parse_message(await websocket.recv())
            message_type = str(message.get('type') or '')
            if message_type == 'ping':
                await websocket.send(json.dumps({'type': 'pong'}))
                continue
            if message_type == 'next':
                await self.chain_event_processor.on_chain_notification(
                    self._extract_chain_id(message, subscribed_chain_id)
                )
                continue
            if message_type == 'complete':
                return
            if message_type == 'error':
                raise RuntimeError(str(message.get('payload')))

    def _parse_message(self, raw_message) -> dict:
        if isinstance(raw_message, dict):
            return raw_message
        return json.loads(raw_message)

    def _extract_chain_id(self, message: dict, subscribed_chain_id: str) -> str:
        payload = (((message.get('payload') or {}).get('data') or {}).get('notifications'))
        if isinstance(payload, dict):
            return str(payload.get('chain_id') or payload.get('chainId') or subscribed_chain_id)
        return subscribed_chain_id

    def _subscription_query(self) -> str:
        return '''
        subscription Notifications($chainId: ChainId!) {
          notifications(chainId: $chainId)
        }
        '''
