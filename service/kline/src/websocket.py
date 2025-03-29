from fastapi import WebSocket


class WebSocketManager:
    def __init__(self):
        self.connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.append(websocket)

    def close(self, websocket: WebSocket):
        self.connections.remove(websocket)

    async def notify(self):
        for connection in self.connections:
            await connection.send_json('{}')

