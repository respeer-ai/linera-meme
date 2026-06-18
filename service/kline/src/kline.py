from fastapi import FastAPI, Request, WebSocket, Query
from fastapi.responses import JSONResponse
import uvicorn
import argparse
import inspect
import time


from swap import Swap
from db import Db, align_timestamp_to_minute_ms
from request_trace import build_api_request_log_line, build_api_trace_context
from kline_debug_service import KlineDebugService
from kline_entrypoint_services import KlineEntrypointServices
from kline_position_metrics_dependencies import KlinePositionMetricsDependencies
from query.handlers.position_metrics import PositionMetricsHandler
from query.read_models.position_metrics import PositionMetricsReadModel
from realtime.market_data_event_queue import MarketDataEventQueue

app = FastAPI()
_swap = None
manager = None
_db = None
_db_config = None
_observability_config = None
_observability_supervisor = None
_observability_facade = None
_entrypoint_services = None
_entrypoint_graph_signature = None
_position_metrics_dependency_overrides = None
_market_data_event_queue = MarketDataEventQueue()


def _reset_entrypoint_graph():
    global _entrypoint_services, _entrypoint_graph_signature
    _entrypoint_services = None
    _entrypoint_graph_signature = None


def _entrypoint_signature():
    services_signature = ()
    if _entrypoint_services is not None:
        services_signature = _entrypoint_services.signature_tuple()
    return (
        _db,
        _observability_config,
        _swap,
        manager,
        _db_config,
        _observability_supervisor,
        _market_data_event_queue,
        *services_signature,
    )


def _services() -> KlineEntrypointServices:
    global _entrypoint_services, _entrypoint_graph_signature
    signature = _entrypoint_signature()
    if _entrypoint_services is None or _entrypoint_graph_signature != signature:
        _entrypoint_services = KlineEntrypointServices(
            db=_db,
            observability_config=_observability_config,
            swap=_swap,
            websocket_manager=manager,
            db_config=_db_config,
            observability_supervisor=_observability_supervisor,
            market_data_event_queue=_market_data_event_queue,
        )
        _entrypoint_graph_signature = signature
    return _entrypoint_services


def _runtime():
    return _services().runtime()


def _lifecycle():
    return _services().lifecycle()


def _debug_service():
    return KlineDebugService(
        runtime=_runtime(),
        position_metrics_public_api=_runtime().position_metrics_public_api(),
        position_metrics_dependencies_factory=_position_metrics_dependencies,
        observability_facade=_observability_facade,
    )

def _build_kline_handler():
    return _runtime().kline_handler()


def _build_transactions_handler():
    return _runtime().transactions_handler()


def _build_positions_handler():
    return _runtime().positions_handler()

def _build_claim_balances_handler():
    return _runtime().claim_balances_handler()


def _business_freshness_service():
    return _runtime().business_freshness_service()


@app.get('/health')
async def on_health():
    return {'status': 'ok'}


def _build_position_metrics_handler():
    dependencies = _position_metrics_dependencies()
    runtime = _runtime()

    return PositionMetricsHandler(
        PositionMetricsReadModel(
            dependencies.positions_repository(),
            dependencies.fetcher(
                position_metrics_public_api=runtime.position_metrics_public_api(),
            ),
            virtual_positions_read_model=runtime.virtual_positions_read_model(),
        ),
        runtime.position_metrics_diagnostic_recorder(),
    )

def _position_metrics_dependency_overrides_resolved():
    if _position_metrics_dependency_overrides is not None:
        return _position_metrics_dependency_overrides
    return {}


def _position_metrics_dependencies():
    return KlinePositionMetricsDependencies.resolve(
        runtime=_runtime(),
        overrides=_position_metrics_dependency_overrides_resolved(),
    )

@app.get('/transactions/audit/replay')
async def on_get_replay_transaction_audit(
    pool_id: int = Query(...),
    pool_application: str = Query(...),
    virtual_initial_liquidity: bool = Query(default=False),
    start_id: int | None = Query(default=None),
    end_id: int | None = Query(default=None),
    swap_out_tolerance_attos: int = Query(default=1),
):
    try:
        return _debug_service().get_replay_transaction_audit(
            pool_id=pool_id,
            pool_application=pool_application,
            virtual_initial_liquidity=virtual_initial_liquidity,
            start_id=start_id,
            end_id=end_id,
            swap_out_tolerance_attos=swap_out_tolerance_attos,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed replay transaction audit: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/points/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}/interval/{interval}')
async def on_get_kline(
    request: Request,
    token0: str,
    token1: str,
    start_at: int,
    end_at: int,
    interval: str,
    pool_id: int | None = Query(default=None),
    pool_application: str | None = Query(default=None),
):
    token_0 = token0
    token_1 = token1
    response_pool_id = pool_id
    response_pool_application = pool_application
    points = []
    raw_start_at = start_at
    raw_end_at = end_at
    request_id = request.query_params.get('request_id')
    trace = build_api_trace_context(request_id, raw_start_at, raw_end_at, interval)
    handler_started_at = time.perf_counter()

    # TODO: align to needed interval
    start_at = align_timestamp_to_minute_ms(start_at)
    end_at = align_timestamp_to_minute_ms(end_at)
    print(build_api_request_log_line(
        'received',
        aligned_end_at=end_at,
        aligned_start_at=start_at,
        client_sent_at_ms=request.query_params.get('client_sent_at_ms') or 'missing',
        interval=interval,
        raw_end_at=trace['raw_end_at'],
        raw_start_at=trace['raw_start_at'],
        received_at_ms=trace['received_at_ms'],
        request_id=trace['request_id'],
    ))

    try:
        payload = _build_kline_handler().get_points(
            token_0=token0,
            token_1=token1,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        response_pool_id = payload['pool_id']
        response_pool_application = payload['pool_application']
        token_0 = payload['token_0']
        token_1 = payload['token_1']
        points = payload['points']
    except Exception as e:
        print(f'Failed get kline: {e}')
    finally:
        print(build_api_request_log_line(
            'completed',
            aligned_end_at=end_at,
            aligned_start_at=start_at,
            duration_ms=int((time.perf_counter() - handler_started_at) * 1000),
            point_count=len(points),
            request_id=trace['request_id'],
        ))

    return {
        'pool_id': response_pool_id,
        'pool_application': response_pool_application,
        'token_0': token_0,
        'token_1': token_1,
        'interval': interval,
        'start_at': start_at,
        'end_at': end_at,
        'points': points,
    }


@app.get('/points/token0/{token0}/token1/{token1}/interval/{interval}/information')
async def on_get_kline_information(
    token0: str,
    token1: str,
    interval: str,
    pool_id: int | None = Query(default=None),
    pool_application: str | None = Query(default=None),
):
    try:
        return _build_kline_handler().get_information(
            token_0=token0,
            token_1=token1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
    except Exception as e:
        print(f'Failed get kline information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/transactions/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}')
async def on_get_transactions(token0: str, token1: str, start_at: int, end_at: int, limit: int | None = None):
    return _build_transactions_handler().get_transactions(
        token_0=token0,
        token_1=token1,
        start_at=start_at,
        end_at=end_at,
        limit=limit,
    )


@app.get('/transactions/start_at/{start_at}/end_at/{end_at}')
async def on_get_combined_transactions(start_at: int, end_at: int, limit: int | None = None):
    return _build_transactions_handler().get_transactions(
        token_0=None,
        token_1=None,
        start_at=start_at,
        end_at=end_at,
        limit=limit,
    )


@app.get('/transactions/token0/{token0}/token1/{token1}/information')
async def on_get_transactions_information(token0: str, token1: str):
    try:
        return _build_transactions_handler().get_information(token_0=token0, token_1=token1)
    except Exception as e:
        print(f'Failed get transactions information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/transactions/information')
async def on_get_combined_transactions_information():
    try:
        return _build_transactions_handler().get_information(token_0=None, token_1=None)
    except Exception as e:
        print(f'Failed get transactions information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/positions')
async def on_get_positions(
    owner: str = Query(...),
    status: str = Query(default='active'),
):
    try:
        response = _build_positions_handler().get_positions(owner=owner, status=status)
        if inspect.isawaitable(response):
            return await response
        return response
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get positions: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/claim-balances')
async def on_get_claim_balances(owner: str = Query(...)):
    try:
        return _build_claim_balances_handler().get_claim_balances(owner=owner)
    except Exception as e:
        print(f'Failed get claim balances: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/position-metrics')
async def on_get_position_metrics(
    owner: str = Query(...),
    status: str = Query(default='active'),
):
    try:
        return await _build_position_metrics_handler().get_position_metrics(
            owner=owner,
            status=status,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get position metrics: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/position-metrics/readiness')
async def on_get_position_metrics_readiness_debug(
    owner: str = Query(...),
    status: str = Query(default='active'),
    sample_limit: int = Query(default=100),
):
    try:
        if sample_limit <= 0:
            raise ValueError('sample_limit must be positive')
        return await _debug_service().build_position_metrics_readiness_debug_payload(
            owner=owner,
            status=status,
            sample_limit=sample_limit,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get position metrics readiness debug: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/diagnostics')
async def on_get_diagnostics(
    source: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    pool_application: str | None = Query(default=None),
    pool_id: int | None = Query(default=None),
    limit: int = Query(default=200),
):
    try:
        return _debug_service().get_diagnostics(
            source=source,
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
            limit=limit,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get diagnostics: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/traces')
async def on_get_debug_traces(
    source: str | None = Query(default=None),
    component: str | None = Query(default=None),
    operation: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    pool_application: str | None = Query(default=None),
    pool_id: int | None = Query(default=None),
    start_at: int | None = Query(default=None),
    end_at: int | None = Query(default=None),
    limit: int = Query(default=200),
):
    try:
        return _debug_service().get_debug_traces(
            source=source,
            component=component,
            operation=operation,
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get debug traces: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/realtime')
async def on_get_realtime_diagnostics(
    stage: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    pool_application: str | None = Query(default=None),
    pool_id: int | None = Query(default=None),
    start_at: int | None = Query(default=None),
    end_at: int | None = Query(default=None),
    limit: int = Query(default=200),
):
    if limit <= 0:
        return JSONResponse(
            status_code=400,
            content={"error": "limit must be positive"},
        )
    if limit > 1000:
        return JSONResponse(
            status_code=400,
            content={"error": "limit must be <= 1000"},
        )
    try:
        return {
            'retention': {
                'ttl_ms': getattr(_db, 'debug_retention_ttl_ms', None),
                'max_rows_per_table': getattr(_db, 'debug_retention_max_rows', None),
            },
            'realtime': _runtime().get_realtime_diagnostics(
                stage=stage,
                event_type=event_type,
                pool_application=pool_application,
                pool_id=pool_id,
                start_at=start_at,
                end_at=end_at,
                limit=limit,
            ),
        }
    except Exception as e:
        print(f'Failed get realtime diagnostics: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/pool')
async def on_get_debug_pool_bundle(
    pool_application: str = Query(...),
    pool_id: int = Query(...),
    owner: str | None = Query(default=None),
    transaction_limit: int = Query(default=1000),
    diagnostics_limit: int = Query(default=200),
):
    try:
        return _debug_service().get_debug_pool_bundle(
            pool_application=pool_application,
            pool_id=pool_id,
            owner=owner,
            transaction_limit=transaction_limit,
            diagnostics_limit=diagnostics_limit,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get debug pool bundle: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post('/debug/catch-up/run')
async def on_post_debug_catch_up_run(
    chain_id: str | None = Query(default=None),
    max_blocks: int | None = Query(default=None),
):
    try:
        return await _debug_service().run_catch_up(
            chain_id=chain_id,
            max_blocks=max_blocks,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed run debug catch-up: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post('/debug/normalization/replay/run')
async def on_post_debug_normalization_replay_run(
    raw_table: str | None = Query(default=None),
    batch_limit: int | None = Query(default=None),
    after_sequence: int | None = Query(default=None),
    ignore_cursor: bool = Query(default=False),
    max_batches: int | None = Query(default=None),
    reprocess_reason: str | None = Query(default=None),
):
    try:
        return await _debug_service().run_normalization_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            after_sequence=after_sequence,
            ignore_cursor=ignore_cursor,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed run debug normalization replay: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post('/debug/market-derivation/replay/run')
async def on_post_debug_market_derivation_replay_run(
    raw_table: str | None = Query(default=None),
    batch_limit: int | None = Query(default=None),
    after_sequence: int | None = Query(default=None),
    ignore_cursor: bool = Query(default=False),
    max_batches: int | None = Query(default=None),
    reprocess_reason: str | None = Query(default=None),
):
    try:
        return await _debug_service().run_market_derivation_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            after_sequence=after_sequence,
            ignore_cursor=ignore_cursor,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed run debug market derivation replay: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/observability')
async def on_get_debug_observability(
    chain_ids: str | None = Query(default=None),
    run_statuses: str | None = Query(default=None),
    anomaly_statuses: str | None = Query(default=None),
    limit: int = Query(default=200),
):
    try:
        return _debug_service().get_debug_observability(
            chain_ids=chain_ids,
            run_statuses=run_statuses,
            anomaly_statuses=anomaly_statuses,
            limit=limit,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed get debug observability: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.post('/debug/observability/recover')
async def on_post_debug_observability_recover():
    try:
        return await _debug_service().recover_observability()
    except Exception as e:
        print(f'Failed recover observability: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/business-freshness')
async def on_get_debug_business_freshness(
    chain_id: str | None = Query(default=None),
    pool_application: str | None = Query(default=None),
):
    try:
        return _business_freshness_service().get_debug_payload(
            chain_id=chain_id,
            pool_application=pool_application,
        )
    except Exception as e:
        print(f'Failed get business freshness debug: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/ticker/interval/{interval}')
async def on_get_ticker(interval: str):
    try:
        stats = _runtime().get_ticker_stats(interval=interval)
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
        stats = _runtime().get_pool_stats(interval=interval)
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
        stats = await _runtime().get_protocol_stats()
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

@app.on_event('startup')
async def on_startup():
    if _swap is None or manager is None or _db_config is None:
        return
    _reset_entrypoint_graph()
    lifecycle = _lifecycle()
    await lifecycle.startup()
    _reset_entrypoint_graph()


@app.on_event('shutdown')
async def on_shutdown():
    lifecycle = _lifecycle()
    await lifecycle.shutdown()
    _reset_entrypoint_graph()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Swap Kline')

    parser.add_argument('--host', type=str, default='0.0.0.0', help='Listened ip')
    parser.add_argument('--port', type=int, default=25080, help='Listened port')
    parser.add_argument('--swap-host', type=str, default='api.lineraswap.fun', help='Host of swap service')
    parser.add_argument('--swap-chain-id', type=str, required=True, help='Swap chain id')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--proxy-host', type=str, default='', help='Host of proxy service')
    parser.add_argument('--proxy-chain-id', type=str, default='', help='Proxy chain id')
    parser.add_argument('--proxy-application-id', type=str, default='', help='Proxy application id')
    parser.add_argument('--database-host', type=str, default='localhost', help='Kline database host')
    parser.add_argument('--database-port', type=str, default='3306', help='Kline database port')
    parser.add_argument('--database-user', type=str, default='debian-sys-maint ', help='Kline database user')
    parser.add_argument('--database-password', type=str, default='4EwQJrNprvw8McZm', help='Kline database password')
    parser.add_argument('--database-name', type=str, default='linera_swap_kline', help='Kline database name')
    parser.add_argument('--clean-kline', action='store_true', help='Clean kline database')
    parser.add_argument('--chain-graphql-url', type=str, default='', help='Linera node service GraphQL URL for raw block ingestion')
    parser.add_argument('--chain-graphql-ws-url', type=str, default='', help='Optional Linera node service GraphQL WebSocket URL for notifications')
    parser.add_argument('--catch-up-chain-ids', type=str, default='', help='Comma-separated chain ids for event-driven/admin catch-up')
    parser.add_argument('--catch-up-max-blocks-per-chain', type=int, default=50, help='Bounded catch-up block limit per chain run')
    parser.add_argument('--catch-up-task-timeout-seconds', type=float, default=30.0, help='Timeout for one bounded catch-up task')
    parser.add_argument('--catch-up-retry-delay-seconds', type=float, default=0.05, help='Delay before scheduling the next catch-up task for an unfinished chain')
    parser.add_argument('--disable-catch-up-on-startup', action='store_true', help='Disable startup reconciliation catch-up for configured chains')
    parser.add_argument('--notification-reconnect-delay-seconds', type=float, default=1.0, help='Reconnect backoff in seconds for Linera notification subscriptions')

    args = parser.parse_args()

    _db_config = {
        'host': args.database_host,
        'port': args.database_port,
        'db_name': args.database_name,
        'username': args.database_user,
        'password': args.database_password,
    }
    parsed_catch_up_chain_ids = tuple(
        chain_id.strip()
        for chain_id in args.catch_up_chain_ids.split(',')
        if chain_id.strip()
    )
    if args.chain_graphql_url:
        _observability_config = {
            'database_host': args.database_host,
            'database_port': args.database_port,
            'database_name': args.database_name,
            'database_username': args.database_user,
            'database_password': args.database_password,
            'chain_graphql_url': args.chain_graphql_url,
            'chain_graphql_ws_url': args.chain_graphql_ws_url or None,
            'catch_up_chain_ids': parsed_catch_up_chain_ids,
            'catch_up_max_blocks_per_chain': args.catch_up_max_blocks_per_chain,
            'catch_up_task_timeout_seconds': args.catch_up_task_timeout_seconds,
            'catch_up_retry_delay_seconds': args.catch_up_retry_delay_seconds,
            'catch_up_on_startup': not args.disable_catch_up_on_startup,
            'notification_reconnect_delay_seconds': args.notification_reconnect_delay_seconds,
            'swap_host': args.swap_host,
            'swap_chain_id': args.swap_chain_id,
            'swap_application_id': args.swap_application_id,
            'proxy_host': args.proxy_host or None,
            'proxy_chain_id': args.proxy_chain_id or None,
            'proxy_application_id': args.proxy_application_id or None,
        }
    _db = Db(args.database_host, args.database_port, args.database_name, args.database_user, args.database_password, args.clean_kline)
    _swap = Swap(
        args.swap_host,
        args.swap_chain_id,
        args.swap_application_id,
        None,
        db=_db,
        query_base_url=f'http://{args.swap_host}/api/swap/query',
    )
    manager = _runtime().build_websocket_manager()
    _reset_entrypoint_graph()
    _observability_facade = _runtime().build_observability_facade()
    _observability_supervisor = _observability_facade.supervisor
    _reset_entrypoint_graph()

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        loop='asyncio',
        http='h11',
        ws_ping_interval=30,
        ws_ping_timeout=10,
    )

    if _db is not None:
        _db.close()
