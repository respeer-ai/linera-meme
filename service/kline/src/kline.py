from fastapi import FastAPI, WebSocket
from fastapi.responses import JSONResponse
import asyncio
import uvicorn
import argparse
import traceback


from swap import Swap
from subscription import WebSocketManager
from ticker import Ticker
from db import Db, align_timestamp_to_minute_ms


app = FastAPI()
_swap = None
manager = None
_ticker = None
_db = None


@app.get('/points/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}/interval/{interval}')
async def on_get_kline(token0: str, token1: str, start_at: int, end_at: int, interval: str):
    token_0 = token0
    token_1 = token1
    points = []

    # TODO: align to needed interval
    start_at = align_timestamp_to_minute_ms(start_at)
    end_at = align_timestamp_to_minute_ms(end_at)

    try:
        (token_0, token_1, points) = _db.get_kline(token_0=token0, token_1=token1, start_at=start_at, end_at=end_at, interval=interval)
    except Exception as e:
        print(f'Failed get kline: {e}')

    return {
        'token_0': token_0,
        'token_1': token_1,
        'interval': interval,
        'start_at': start_at,
        'end_at': end_at,
        'points': points,
    }


@app.get('/points/token0/{token0}/token1/{token1}/interval/{interval}/information')
async def on_get_kline_information(token0: str, token1: str, interval: str):
    try:
        return _db.get_kline_information(token_0=token0, token_1=token1, interval=interval)
    except Exception as e:
        print(f'Failed get kline information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/transactions/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}')
async def on_get_transactions(token0: str, token1: str, start_at: int, end_at: int):
    return _db.get_transactions(token_0=token0, token_1=token1, start_at=start_at, end_at=end_at)


@app.get('/transactions/start_at/{start_at}/end_at/{end_at}')
async def on_get_combined_transactions(start_at: int, end_at: int):
    return _db.get_transactions(token_0=None, token_1=None, start_at=start_at, end_at=end_at)


@app.get('/transactions/token0/{token0}/token1/{token1}/information')
async def on_get_transactions_information(token0: str, token1: str):
    try:
        return _db.get_transactions_information(token_0=token0, token_1=token1)
    except Exception as e:
        print(f'Failed get transactions information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/transactions/information')
async def on_get_combined_transactions_information():
    try:
        return _db.get_transactions_information(token_0=None, token_1=None)
    except Exception as e:
        print(f'Failed get transactions information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/ticker/interval/{interval}')
async def on_get_ticker(interval: str):
    try:
        stats =  _db.get_ticker(interval=interval)
        return {
            'interval': interval,
            'stats': stats,
        }
    except Exception as e:
        print(f'Failed get ticker: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get('/poolstats/interval/{interval}')
async def on_get_pool_stats(interval: str):
    try:
        stats =  _db.get_pool_stats(interval=interval)
        return {
            'interval': interval,
            'stats': stats,
        }
    except Exception as e:
        print(f'Failed get ticker: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get('/protocol/stats')
async def get_protocol_stats() -> dict:
    try:
        pools = await _swap.get_pools()
        stats = _db.get_protocol_stats(pools)
        return stats
    except Exception as e:
        print(f'Failed get protocol stats: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.websocket('/ws')
async def on_subscribe(websocket: WebSocket):
    await websocket.accept()
    await manager.connect(websocket)


## Must not exposed
@app.post('/run/ticker')
async def on_run_ticker():
    global _ticker
    if _ticker is not None:
        return
    _ticker = Ticker(manager, _swap, _db)
    while _ticker.running():
        try:
            await _ticker.run()
        except Exception as e:
            print(f'Ticker quiting ... {e}')
            traceback.print_exc()
            await asyncio.sleep(10)

# Http and websocket must be deployed to different pod


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Swap Kline')

    parser.add_argument('--host', type=str, default='0.0.0.0', help='Listened ip')
    parser.add_argument('--port', type=int, default=25080, help='Listened port')
    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--swap-chain-id', type=str, required=True, help='Swap chain id')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--database-host', type=str, default='localhost', help='Kline database host')
    parser.add_argument('--database-port', type=str, default='3306', help='Kline database port')
    parser.add_argument('--database-user', type=str, default='debian-sys-maint ', help='Kline database user')
    parser.add_argument('--database-password', type=str, default='4EwQJrNprvw8McZm', help='Kline database password')
    parser.add_argument('--database-name', type=str, default='linera_swap_kline', help='Kline database name')
    parser.add_argument('--clean-kline', action='store_true', help='Clean kline database')

    args = parser.parse_args()

    _swap = Swap(args.swap_host, args.swap_chain_id, args.swap_application_id, None)

    _db = Db(args.database_host, args.database_port, args.database_name, args.database_user, args.database_password, args.clean_kline)
    manager = WebSocketManager(_swap, _db)

    uvicorn.run(app, host=args.host, port=args.port, ws_ping_interval=30, ws_ping_timeout=10)

    if _db is not None:
        _db.close()
    if _ticker is not None:
        _ticker.stop()
