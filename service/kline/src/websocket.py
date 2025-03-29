from fastapi import WebSocket
import json


class WebSocketManager:
    def __init__(self, swap, db):
        self.connections: list[WebSocket] = []
        self.swap = swap
        self.db = db

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def close(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def notify(self):
        points = {}
        intervals = ['1T', '5T', '10T', '1H', '1D', '1W', '1M']

        pools = self.swap.get_pools()
        for interval in intervals:
            interval_points = []
            for pool in pools:
                (start_at, end_at, _points, interval) = self.db.get_last_kline(pool.token_0, pook.token_1, interval)
                interval_points.append({
                    'token_0': pool.token_0,
                    'token_1': pool.token_1,
                    'interval': interval,
                    'start_at': start_at,
                    'end_at': end_at,
                    'points': _points,
                })
                (start_at, end_at, _points, interval) = self.db.get_last_kline(pool.token_1, pook.token_0, interval)
                interval_points.append({
                    'token_0': pool.token_1,
                    'token_1': pool.token_0,
                    'interval': interval,
                    'start_at': start_at,
                    'end_at': end_at,
                    'points': _points,
                })
            points.extend(interval_points)

        for connection in self.connections:
            await connection.send_json({
                'notification': 'kline',
                'value': json.dumps(points)
            })

