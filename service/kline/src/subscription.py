from fastapi import WebSocket
from dataclasses import dataclass


@dataclass(frozen=True)
class KlineSubscription:
    token_0: str
    token_1: str
    interval: str


class WebSocketManager:
    def __init__(self, swap, db):
        self.connections: list[WebSocket] = []
        self.kline_subscriptions: dict[WebSocket, set[KlineSubscription]] = {}
        self.swap = swap
        self.db = db

    async def connect(self, websocket: WebSocket):
        print(f'New connection {len(self.connections)} from {websocket.scope["client"]}')
        self.connections.append(websocket)
        self.kline_subscriptions[websocket] = set()
        await self.handle(websocket)

    def close(self, websocket: WebSocket):
        if websocket in self.connections:
            self.connections.remove(websocket)
        self.kline_subscriptions.pop(websocket, None)

    def handle_message(self, websocket: WebSocket, data):
        if not isinstance(data, dict):
            return

        if data.get('action') == 'subscribe' and data.get('topic') == 'kline':
            token_0 = data.get('token_0')
            token_1 = data.get('token_1')
            intervals = data.get('intervals') or []

            if not token_0 or not token_1 or len(intervals) == 0:
                return

            self.kline_subscriptions[websocket] = {
                KlineSubscription(
                    token_0=token_0,
                    token_1=token_1,
                    interval=interval,
                )
                for interval in intervals
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

    async def notify_kline(self, payload=None):
        intervals = ['1min', '5min', '10min', '1h', '1D', '1W', '1ME']

        pools = None if payload is not None else await self.swap.get_pools()
        for connection in self.connections:
            subscriptions = self.kline_subscriptions.get(connection) or set()
            points = {}

            if payload is not None and len(subscriptions) > 0:
                points = self.filter_incremental_kline_payload(payload, subscriptions)
                if len(points) == 0:
                    continue
            elif len(subscriptions) == 0:
                for interval in intervals:
                    interval_points = []
                    for pool in pools:
                        (token_0, token_1, start_at, end_at, interval, _points) = self.db.get_last_kline(pool.token_0, pool.token_1, interval)
                        interval_points.append({
                            'token_0': token_0,
                            'token_1': token_1,
                            'interval': interval,
                            'start_at': start_at,
                            'end_at': end_at,
                            'points': _points,
                        })
                        (token_0, token_1, start_at, end_at, interval, _points) = self.db.get_last_kline(pool.token_1, pool.token_0, interval)
                        interval_points.append({
                            'token_0': token_0,
                            'token_1': token_1,
                            'interval': interval,
                            'start_at': start_at,
                            'end_at': end_at,
                            'points': _points,
                        })
                    points[interval] = interval_points
            else:
                for subscription in subscriptions:
                    (token_0, token_1, start_at, end_at, interval, _points) = self.db.get_last_kline(
                        subscription.token_0,
                        subscription.token_1,
                        subscription.interval,
                    )
                    interval_points = points.get(subscription.interval, [])
                    interval_points.append({
                        'token_0': token_0,
                        'token_1': token_1,
                        'interval': interval,
                        'start_at': start_at,
                        'end_at': end_at,
                        'points': _points,
                    })
                    points[subscription.interval] = interval_points

            await connection.send_json({
                'notification': 'kline',
                'value': points
            })

    async def notify(self, topic: str, payload):
        if topic == 'kline':
            await self.notify_kline(payload)
        elif topic == 'transactions':
            await self.notify_transactions(payload)
