import argparse
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import time
import uvicorn

import async_request
from db import Db
from maker_api_runtime import MakerApiRuntime


app = FastAPI()
_db = None
_config = {
    'wallet_url': '',
    'wallet_metrics_url': '',
    'wallet_owner': '',
    'wallet_memory_limit_bytes': 0,
}


def now_ms() -> int:
    return int(time.time() * 1000)


def parse_prometheus_metrics(body: str):
    return _runtime().parse_prometheus_metrics(body)


def summarize_wallet_metrics(metrics: dict):
    return _runtime().summarize_wallet_metrics(metrics)


async def fetch_wallet_metrics():
    return await _runtime().fetch_wallet_metrics()


async def fetch_wallet_balances(chain_id: str | None, owner: str | None):
    return await _runtime().fetch_wallet_balances(chain_id, owner)


async def post_wallet_query(payload: dict, timeout=(3, 10)):
    return await _runtime().post_wallet_query(payload, timeout=timeout)


async def fetch_wallet_block(chain_id: str, block_hash: str):
    return await _runtime().fetch_wallet_block(chain_id, block_hash)


async def fetch_wallet_pending_messages(chain_id: str):
    return await _runtime().fetch_wallet_pending_messages(chain_id)


def build_wallet_health(metrics_result, balances_result):
    return _runtime().build_wallet_health(metrics_result, balances_result)


async def build_wallet_snapshot(include_metrics: bool, include_balances: bool):
    return await _runtime().build_wallet_snapshot(include_metrics, include_balances)


async def build_wallet_index(include_metrics: bool, include_balances: bool):
    return await _runtime().build_wallet_index(include_metrics, include_balances)


def group_latest_by(rows: list, key_builder):
    return _runtime().group_latest_by(rows, key_builder)

def _runtime():
    return MakerApiRuntime(
        db=_db,
        config=_config,
        request_client=async_request,
        clock_ms=lambda: globals()['now_ms'](),
    )


@app.get('/events/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}')
async def on_get_maker_events(token0: str, token1: str, start_at: int, end_at: int):
    return _runtime().get_maker_events(token0, token1, start_at, end_at)


@app.get('/events/start_at/{start_at}/end_at/{end_at}')
async def on_get_combined_maker_events(start_at: int, end_at: int):
    return _runtime().get_combined_maker_events(start_at, end_at)


@app.get('/events/token0/{token0}/token1/{token1}/information')
async def on_get_maker_events_information(token0: str, token1: str):
    try:
        return _runtime().get_maker_events_information(token0, token1)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/events/information')
async def on_get_combined_maker_events_information():
    try:
        return _runtime().get_maker_events_information(None, None)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/wallet')
async def on_get_debug_wallet(
    include_metrics: bool = Query(default=True),
    include_balances: bool = Query(default=True),
):
    try:
        return await _runtime().build_wallet_snapshot(include_metrics, include_balances)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/wallet/metrics')
async def on_get_debug_wallet_metrics():
    try:
        return await _runtime().get_debug_wallet_metrics()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/wallet/balances')
async def on_get_debug_wallet_balances():
    try:
        return await _runtime().get_debug_wallet_balances()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/wallet/block')
async def on_get_debug_wallet_block(chain_id: str, block_hash: str):
    try:
        return await _runtime().get_debug_wallet_block(chain_id, block_hash)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/wallet/pending-messages')
async def on_get_debug_wallet_pending_messages(chain_id: str):
    try:
        return await _runtime().get_debug_wallet_pending_messages(chain_id)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/traces')
async def on_get_debug_traces(
    source: str | None = Query(default='maker'),
    component: str | None = Query(default=None),
    operation: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    pool_application: str | None = Query(default=None),
    pool_id: int | None = Query(default=None),
    start_at: int | None = Query(default=None),
    end_at: int | None = Query(default=None),
    limit: int = Query(default=200),
    include_payloads: bool = Query(default=False),
):
    try:
        return _runtime().get_debug_traces(
            source=source,
            component=component,
            operation=operation,
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
            include_payloads=include_payloads,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/pools/stall')
async def on_get_debug_pools_stall(
    pool_id: int | None = Query(default=None),
    owner: str | None = Query(default=None),
    lookback_minutes: int = Query(default=360),
    stall_seconds: int = Query(default=900),
    include_wallets: bool = Query(default=True),
):
    try:
        return await _runtime().get_debug_pools_stall(
            pool_id=pool_id,
            owner=owner,
            lookback_minutes=lookback_minutes,
            stall_seconds=stall_seconds,
            include_wallets=include_wallets,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/health')
async def on_get_debug_health():
    try:
        return await _runtime().get_debug_health()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.on_event('shutdown')
async def on_shutdown():
    global _db
    if _db is not None:
        _runtime().close()
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
    parser.add_argument('--wallet-url', type=str, required=True, help='Maker wallet RPC URL')
    parser.add_argument('--wallet-owner', type=str, default='', help='Maker wallet owner')
    parser.add_argument('--wallet-metrics-url', type=str, required=True, help='Maker wallet metrics URL')
    parser.add_argument('--wallet-memory-limit-bytes', type=int, default=0, help='Maker wallet memory limit')

    args = parser.parse_args()

    _config['wallet_url'] = args.wallet_url
    _config['wallet_owner'] = args.wallet_owner
    _config['wallet_metrics_url'] = args.wallet_metrics_url
    _config['wallet_memory_limit_bytes'] = int(args.wallet_memory_limit_bytes)

    _db = Db(
        args.database_host,
        args.database_port,
        args.database_name,
        args.database_user,
        args.database_password,
        False,
    )

    uvicorn.run(app, host=args.host, port=args.port, ws_ping_interval=30, ws_ping_timeout=10)
