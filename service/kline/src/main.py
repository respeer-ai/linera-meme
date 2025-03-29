from fastapi import FastAPI, WebSocket
import pandas as pd
import asyncio
import uvicorn
import argparse


from swap import Swap
from websocket import WebSocketManager
from ticker import Ticker
from db import Db


app = FastAPI()
_swap = None
manager = None
_ticker = None
_db = None


@app.get('/kline/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}/interval/{interval}')
async def on_get_kline(token0: str, token1: str, start_at: int, end_at: int, interval: str):
    points = _db.get_kline(token_0=token0, token_1=token1, start_at=start_at, end_at=end_at, interval=interval)
    return {
        'token_0': token0,
        'token_1': token1,
        'interval': interval,
        'start_at': start_at,
        'end_at': end_at,
        'points': points,
    }


@app.websocket('/ws')
async def on_subscribe(websocket: WebSocket):
    await websocket.accept()
    manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # TODO: process incoming data
    except Exception as e:
        print(f"Error: {e}")
    finally:
        manager.close(websocket)


## Must not exposed
@app.post('/run/ticker')
async def on_subscribe():
    _ticker = Ticker(manager, _swap, _db)
    await _ticker.run()

# Http and websocket must be deployed to different pod


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Swap Kline')

    parser.add_argument('--host', type=str, default='0.0.0.0', help='Listened ip')
    parser.add_argument('--port', type=int, default=25080, help='Listened port')
    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--database-host', type=str, default='172.16.31.42', help='Kline database host')
    parser.add_argument('--database-user', type=str, default='debian-sys-maint ', help='Kline database user')
    parser.add_argument('--database-password', type=str, default='SwZoiC7n8azn1EKG', help='Kline database password')
    parser.add_argument('--database-name', type=str, default='linera_swap_kline', help='Kline database name')

    args = parser.parse_args()

    _swap = Swap(args.swap_host)
    _swap.get_swap_chain()
    _swap.get_swap_application()

    _db = Db(args.database_host, args.database_name, args.database_user, args.database_password)
    manager = WebSocketManager(_swap, _db)

    uvicorn.run(app, host=args.host, port=args.port)

    if _db is not None:
        _db.close()
    if _ticker is not None:
        _ticker.stop()
