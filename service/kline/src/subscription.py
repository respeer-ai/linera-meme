from fastapi import WebSocket
from dataclasses import dataclass
from account_codec import AccountCodec
from candle_schema import normalize_interval_for_api


@dataclass(frozen=True)
class KlineSubscription:
    token_0: str
    token_1: str
    interval: str
    pool_id: int | None = None
    pool_application: str | None = None


@dataclass(frozen=True)
class PositionsSubscription:
    owner: str | None = None
    pool_id: int | None = None
    pool_application: str | None = None


class WebSocketManager:
    def __init__(self, swap, candle_reader, pool_catalog_repository=None):
        self.connections: list[WebSocket] = []
        self.kline_subscriptions: dict[WebSocket, set[KlineSubscription]] = {}
        self.positions_subscriptions: dict[WebSocket, set[PositionsSubscription]] = {}
        self.swap = swap
        self.candle_reader = candle_reader
        self.pool_catalog_repository = pool_catalog_repository
        self.account_codec = AccountCodec()

    async def connect(self, websocket: WebSocket):
        print(f'New connection {len(self.connections)} from {websocket.scope["client"]}')
        self.connections.append(websocket)
        self.kline_subscriptions[websocket] = set()
        self.positions_subscriptions[websocket] = set()
        await self.handle(websocket)

    def close(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        self.kline_subscriptions.pop(websocket, None)
        self.positions_subscriptions.pop(websocket, None)

    def handle_message(self, websocket: WebSocket, data):
        if not isinstance(data, dict):
            return

        if data.get('action') == 'subscribe' and data.get('topic') == 'kline':
            token_0 = data.get('token_0')
            token_1 = data.get('token_1')
            intervals = data.get('intervals') or []
            pool_id = data.get('pool_id')
            pool_application = data.get('pool_application')

            if not token_0 or not token_1 or len(intervals) == 0:
                return

            self.kline_subscriptions[websocket] = {
                KlineSubscription(
                    token_0=token_0,
                    token_1=token_1,
                    interval=interval,
                    pool_id=pool_id,
                    pool_application=pool_application,
                )
                for interval in intervals
            }
        if data.get('action') == 'subscribe' and data.get('topic') == 'positions':
            self.positions_subscriptions[websocket] = {
                PositionsSubscription(
                    owner=data.get('owner'),
                    pool_id=data.get('pool_id'),
                    pool_application=data.get('pool_application'),
                )
            }

    def filter_incremental_kline_payload(self, payload, subscriptions: set[KlineSubscription]):
        filtered = {}

        for interval, interval_points in payload.items():
            matching_points = [
                points
                for points in interval_points
                if KlineSubscription(
                    token_0=points.get('token_0'),
                    token_1=points.get('token_1'),
                    interval=interval,
                    pool_id=points.get('pool_id'),
                    pool_application=points.get('pool_application'),
                ) in subscriptions
            ]
            if len(matching_points) > 0:
                filtered[interval] = matching_points

        return filtered

    async def handle(self, websocket: WebSocket):
        try:
            while True:
                self.handle_message(websocket, await websocket.receive_json())
        except Exception as e:
            print(f'{websocket.scope["client"]}: {e}')
        finally:
            self.close(websocket)

    async def notify_transactions(self, payload):
        for connection in self.connections:
            await connection.send_json({
                'notification': 'transactions',
                'value': payload
            })

    def filter_positions_payload(self, payload, subscriptions: set[PositionsSubscription]):
        if len(subscriptions) == 0:
            return payload
        filtered_events = []
        for event in payload.get('events') or []:
            owners = set(event.get('owners') or [])
            for subscription in subscriptions:
                owner_matches = (
                    subscription.owner is None
                    or len(owners) == 0
                    or subscription.owner in owners
                )
                pool_id_matches = subscription.pool_id is None or subscription.pool_id == event.get('pool_id')
                pool_application_matches = (
                    subscription.pool_application is None
                    or subscription.pool_application == event.get('pool_application')
                )
                if owner_matches and pool_id_matches and pool_application_matches:
                    filtered_events.append(event)
                    break
        return {'events': filtered_events}

    async def notify_positions(self, payload):
        for connection in self.connections:
            subscriptions = self.positions_subscriptions.get(connection) or set()
            filtered = self.filter_positions_payload(payload, subscriptions)
            if not filtered.get('events'):
                continue
            await connection.send_json({
                'notification': 'positions',
                'value': filtered,
            })

    async def notify_kline(self, payload=None):
        intervals = ['1min', '5min', '10min', '15min', '1h', '4h', '1d', '1w', '1ME']

        pools = None
        if payload is None:
            if self.pool_catalog_repository is None:
                raise RuntimeError('Projection pool catalog repository is required for websocket kline broadcast')
            pools = self.pool_catalog_repository.list_current_pool_views()
        for connection in self.connections:
            subscriptions = self.kline_subscriptions.get(connection) or set()
            points = {}

            if payload is not None:
                if len(subscriptions) > 0:
                    points = self.filter_incremental_kline_payload(payload, subscriptions)
                    if len(points) == 0:
                        continue
                else:
                    points = payload
            elif len(subscriptions) == 0:
                for interval in intervals:
                    interval_points = []
                    for pool in pools:
                        pool_application = self.account_codec.format_account(
                            chain_id=pool.pool_application.chain_id,
                            owner=pool.pool_application.owner,
                        )
                        point_payload = self.candle_reader.get_last_points(
                            token_0=pool.token_0,
                            token_1=pool.token_1,
                            interval=interval,
                            pool_id=pool.pool_id,
                            pool_application=pool_application,
                        )
                        interval_points.append(point_payload)
                        point_payload = self.candle_reader.get_last_points(
                            token_0=pool.token_1,
                            token_1=pool.token_0,
                            interval=interval,
                            pool_id=pool.pool_id,
                            pool_application=pool_application,
                        )
                        interval_points.append(point_payload)
                    points[interval] = interval_points
            else:
                for subscription in subscriptions:
                    point_payload = self.candle_reader.get_last_points(
                        token_0=subscription.token_0,
                        token_1=subscription.token_1,
                        interval=subscription.interval,
                        pool_id=subscription.pool_id,
                        pool_application=subscription.pool_application,
                    )
                    interval_points = points.get(subscription.interval, [])
                    interval_points.append(point_payload)
                    points[subscription.interval] = interval_points

            await connection.send_json({
                'notification': 'kline',
                'value': {
                    normalize_interval_for_api(interval): interval_points
                    for interval, interval_points in points.items()
                },
            })

    async def notify(self, topic: str, payload):
        if topic == 'kline':
            await self.notify_kline(payload)
        elif topic == 'transactions':
            await self.notify_transactions(payload)
        elif topic == 'positions':
            await self.notify_positions(payload)
