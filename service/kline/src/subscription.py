from fastapi import WebSocket
import json


class WebSocketManager:
    def __init__(self, swap, db):
        self.connections: list[WebSocket] = []
        self.swap = swap
        self.db = db

    async def connect(self, websocket: WebSocket):
        print(f'New connection {len(self.connections)} from {websocket.scope["client"]}')
        self.connections.append(websocket)
        await self.handle(websocket)

    def close(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def handle(self, websocket: WebSocket):
        try:
            while True:
                data = await websocket.receive_json()
                # TODO: process incoming data
        except Exception as e:
            print(f'{websocket.scope["client"]}: {e}')
        finally:
            self.close(websocket)

    async def notify(self):
        points = {}
        intervals = ['1min', '5min', '10min', '1h', '1D', '1W', '1ME']

        pools = self.swap.get_pools()
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
                    'points': _points.to_json(),
                })
                (token_0, token_1, start_at, end_at, interval, _points) = self.db.get_last_kline(pool.token_1, pool.token_0, interval)
                interval_points.append({
                    'token_0': pool.token_1,
                    'token_1': pool.token_0,
                    'interval': interval,
                    'start_at': start_at,
                    'end_at': end_at,
                    'points': _points.to_json(),
                })
            points[interval] = interval_points

        for connection in self.connections:
            await connection.send_json({
                'notification': 'kline',
                'value': json.dumps(points)
            })

