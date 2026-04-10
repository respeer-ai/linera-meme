from fastapi import FastAPI
from fastapi.responses import JSONResponse
import argparse
import uvicorn

from db import Db


app = FastAPI()
_db = None


@app.get('/events/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}')
async def on_get_maker_events(token0: str, token1: str, start_at: int, end_at: int):
    return _db.get_maker_events(token_0=token0, token_1=token1, start_at=start_at, end_at=end_at)


@app.get('/events/start_at/{start_at}/end_at/{end_at}')
async def on_get_combined_maker_events(start_at: int, end_at: int):
    return _db.get_maker_events(token_0=None, token_1=None, start_at=start_at, end_at=end_at)


@app.get('/events/token0/{token0}/token1/{token1}/information')
async def on_get_maker_events_information(token0: str, token1: str):
    try:
        return _db.get_maker_events_information(token_0=token0, token_1=token1)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/events/information')
async def on_get_combined_maker_events_information():
    try:
        return _db.get_maker_events_information(token_0=None, token_1=None)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.on_event('shutdown')
async def on_shutdown():
    global _db
    if _db is not None:
        _db.close()
        _db = None


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Maker API')

    parser.add_argument('--host', type=str, default='0.0.0.0', help='Listened ip')
    parser.add_argument('--port', type=int, default=8080, help='Listened port')
    parser.add_argument('--database-host', type=str, default='localhost', help='Maker database host')
    parser.add_argument('--database-port', type=str, default='3306', help='Maker database port')
    parser.add_argument('--database-user', type=str, default='debian-sys-maint ', help='Maker database user')
    parser.add_argument('--database-password', type=str, default='4EwQJrNprvw8McZm', help='Maker database password')
    parser.add_argument('--database-name', type=str, default='linera_swap_kline', help='Maker database name')

    args = parser.parse_args()

    _db = Db(
        args.database_host,
        args.database_port,
        args.database_name,
        args.database_user,
        args.database_password,
        False,
    )

    uvicorn.run(app, host=args.host, port=args.port, ws_ping_interval=30, ws_ping_timeout=10)
