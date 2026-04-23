from fastapi import FastAPI, Request, WebSocket, Query
from fastapi.responses import JSONResponse
import asyncio
import uvicorn
import argparse
import traceback
import time
import async_request
from environment import running_in_k8s
import position_metrics


from swap import Swap
from subscription import WebSocketManager
from ticker import Ticker
from db import Db, align_timestamp_to_minute_ms
from request_trace import build_api_request_log_line, build_api_trace_context
from storage.mysql.projection_repo import ProjectionRepository
from query.read_models.candles import CandlesReadModel
from query.read_models.transactions import TransactionsReadModel
from query.read_models.positions import PositionsReadModel
from query.handlers.kline import KlineHandler
from query.handlers.transactions import TransactionsHandler
from query.handlers.positions import PositionsHandler
from query.handlers.priority_one_rollout import PriorityOneRollout
from query.serializers.kline import KlineSerializer
from query.serializers.transactions import TransactionsSerializer
from query.serializers.positions import PositionsSerializer


app = FastAPI()
_swap = None
manager = None
_ticker = None
_ticker_task = None
_db = None
_ticker_db = None
_db_config = None


def _build_priority1_rollout() -> PriorityOneRollout:
    return PriorityOneRollout(_db)


def _build_projection_repository():
    if _db is None:
        raise RuntimeError('Db client is not initialized')
    return ProjectionRepository(_db)


def _build_kline_handler() -> KlineHandler:
    repository = _build_projection_repository()
    return KlineHandler(CandlesReadModel(repository), KlineSerializer())


def _build_transactions_handler() -> TransactionsHandler:
    repository = _build_projection_repository()
    return TransactionsHandler(TransactionsReadModel(repository), TransactionsSerializer())


def _build_positions_handler() -> PositionsHandler:
    repository = _build_projection_repository()
    return PositionsHandler(PositionsReadModel(repository), PositionsSerializer())


def _get_kline_legacy(
    *,
    token_0: str,
    token_1: str,
    start_at: int,
    end_at: int,
    interval: str,
    pool_id: int | None = None,
    pool_application: str | None = None,
) -> dict:
    response_pool_id, response_pool_application, resolved_token_0, resolved_token_1, points = _db.get_kline(
        token_0=token_0,
        token_1=token_1,
        start_at=start_at,
        end_at=end_at,
        interval=interval,
        pool_id=pool_id,
        pool_application=pool_application,
    )
    return {
        'pool_id': response_pool_id,
        'pool_application': response_pool_application,
        'token_0': resolved_token_0,
        'token_1': resolved_token_1,
        'interval': interval,
        'start_at': start_at,
        'end_at': end_at,
        'points': points,
    }


def _get_kline_information_legacy(
    *,
    token_0: str,
    token_1: str,
    interval: str,
    pool_id: int | None = None,
    pool_application: str | None = None,
):
    return _db.get_kline_information(
        token_0=token_0,
        token_1=token_1,
        interval=interval,
        pool_id=pool_id,
        pool_application=pool_application,
    )


def _get_transactions_legacy(
    *,
    token_0: str | None,
    token_1: str | None,
    start_at: int,
    end_at: int,
):
    return _db.get_transactions(
        token_0=token_0,
        token_1=token_1,
        start_at=start_at,
        end_at=end_at,
    )


def _get_transactions_information_legacy(
    *,
    token_0: str | None,
    token_1: str | None,
):
    return _db.get_transactions_information(token_0=token_0, token_1=token_1)


def _get_positions_legacy(
    *,
    owner: str,
    status: str,
):
    return {
        'owner': owner,
        'positions': _db.get_positions(owner=owner, status=status),
    }


async def _default_position_metrics_fetcher(position: dict):
    if _swap is None:
        raise RuntimeError('Swap client is not initialized')
    if _db is None:
        raise RuntimeError('Db client is not initialized')
    return await position_metrics.fetch_live_position_metrics(
        position,
        _swap.base_url,
        liquidity_history=_db.get_position_liquidity_history(
            owner=position['owner'],
            pool_application=position['pool_application'],
            pool_id=position['pool_id'],
        ),
        pool_transaction_history=_db.get_pool_transaction_history(
            pool_application=position['pool_application'],
            pool_id=position['pool_id'],
        ),
        pool_swap_count_since_open=_db.get_pool_swap_count_since(
            pool_application=position['pool_application'],
            pool_id=position['pool_id'],
            created_at=position['opened_at'],
        ),
        pool_history_gap_summary=_db.get_pool_transaction_gap_summary(
            pool_application=position['pool_application'],
            pool_id=position['pool_id'],
        ),
        post=async_request.post,
        in_k8s=running_in_k8s(),
    )


_position_metrics_fetcher = _default_position_metrics_fetcher


async def _fetch_live_pool_transaction_ids(
    pool_application: str,
    *,
    recent_window: int,
):
    if _swap is None:
        raise RuntimeError('Swap client is not initialized')

    url = position_metrics.pool_application_url(
        _swap.base_url,
        pool_application,
        in_k8s=running_in_k8s(),
    )
    response = await async_request.post(
        url=url,
        json={'query': 'query {\n latestTransactions \n}'},
        timeout=(3, 10),
    )
    response.raise_for_status()
    payload = response.json()
    if 'errors' in payload:
        raise RuntimeError(str(payload['errors']))

    latest_transactions = payload['data']['latestTransactions'] or []
    latest_ids = sorted(
        int(transaction['transactionId'])
        for transaction in latest_transactions
        if transaction.get('transactionId') is not None
    )
    if recent_window > 0 and len(latest_ids) > recent_window:
        latest_ids = latest_ids[-recent_window:]
    return latest_ids


async def _build_recent_transaction_window_audit(
    *,
    pool_id: int,
    pool_application: str,
    recent_window: int,
):
    if _db is None:
        raise RuntimeError('Db client is not initialized')
    if recent_window <= 0:
        raise ValueError('recent_window must be positive')

    live_ids = await _fetch_live_pool_transaction_ids(
        pool_application,
        recent_window=recent_window,
    )
    if not live_ids:
        return {
            'pool_id': pool_id,
            'pool_application': pool_application,
            'recent_window': recent_window,
            'window_start_id': None,
            'window_end_id': None,
            'live_ids': [],
            'db_ids': [],
            'missing_in_db': [],
            'missing_in_live': [],
        }

    window_start_id = live_ids[0]
    window_end_id = live_ids[-1]
    db_ids = _db.get_pool_transaction_ids(
        pool_id=pool_id,
        pool_application=pool_application,
        start_id=window_start_id,
        end_id=window_end_id,
    )
    live_id_set = set(live_ids)
    db_id_set = set(db_ids)

    return {
        'pool_id': pool_id,
        'pool_application': pool_application,
        'recent_window': recent_window,
        'window_start_id': window_start_id,
        'window_end_id': window_end_id,
        'live_ids': live_ids,
        'db_ids': db_ids,
        'missing_in_db': sorted(live_id_set - db_id_set),
        'missing_in_live': sorted(db_id_set - live_id_set),
    }


@app.get('/transactions/audit/recent')
async def on_get_recent_transaction_audit(
    pool_id: int = Query(...),
    pool_application: str = Query(...),
    recent_window: int = Query(default=5000),
):
    try:
        return await _build_recent_transaction_window_audit(
            pool_id=pool_id,
            pool_application=pool_application,
            recent_window=recent_window,
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={"error": str(e)}
        )
    except Exception as e:
        print(f'Failed audit recent transactions: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
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
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if swap_out_tolerance_attos < 0:
            raise ValueError('swap_out_tolerance_attos must be non-negative')

        pool_transaction_history = _db.get_pool_transaction_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        if start_id is not None or end_id is not None:
            lower_bound = int(start_id or 0)
            upper_bound = int(end_id or (2 ** 32 - 1))
            pool_transaction_history = [
                tx
                for tx in pool_transaction_history
                if lower_bound <= int(tx.get('transaction_id') or 0) <= upper_bound
            ]

        return {
            'pool_id': pool_id,
            'pool_application': pool_application,
            'virtual_initial_liquidity': virtual_initial_liquidity,
            'start_id': start_id,
            'end_id': end_id,
            'swap_out_tolerance_attos': swap_out_tolerance_attos,
            'audit': position_metrics.inspect_pool_history_replay(
                pool_transaction_history,
                virtual_initial_liquidity=virtual_initial_liquidity,
                swap_out_tolerance_attos=swap_out_tolerance_attos,
            ),
        }
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
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            payload = _get_kline_legacy(
                token_0=token0,
                token_1=token1,
                start_at=start_at,
                end_at=end_at,
                interval=interval,
                pool_id=pool_id,
                pool_application=pool_application,
            )
        else:
            payload = _build_kline_handler().get_points(
                token_0=token0,
                token_1=token1,
                start_at=start_at,
                end_at=end_at,
                interval=interval,
                pool_id=pool_id,
                pool_application=pool_application,
            )
            legacy_payload = _get_kline_legacy(
                token_0=token0,
                token_1=token1,
                start_at=start_at,
                end_at=end_at,
                interval=interval,
                pool_id=pool_id,
                pool_application=pool_application,
            )
            rollout.compare(
                endpoint='/points',
                legacy_payload=legacy_payload,
                new_payload=payload,
                pool_application=payload['pool_application'],
                pool_id=payload['pool_id'],
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
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            return _get_kline_information_legacy(
                token_0=token0,
                token_1=token1,
                interval=interval,
                pool_id=pool_id,
                pool_application=pool_application,
            )
        payload = _build_kline_handler().get_information(
            token_0=token0,
            token_1=token1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        legacy_payload = _get_kline_information_legacy(
            token_0=token0,
            token_1=token1,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        rollout.compare(
            endpoint='/points/information',
            legacy_payload=legacy_payload,
            new_payload=payload,
            pool_application=pool_application,
            pool_id=pool_id,
        )
        return payload
    except Exception as e:
        print(f'Failed get kline information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/transactions/token0/{token0}/token1/{token1}/start_at/{start_at}/end_at/{end_at}')
async def on_get_transactions(token0: str, token1: str, start_at: int, end_at: int):
    rollout = _build_priority1_rollout()
    if rollout.use_legacy():
        return _get_transactions_legacy(
            token_0=token0,
            token_1=token1,
            start_at=start_at,
            end_at=end_at,
        )
    payload = _build_transactions_handler().get_transactions(
        token_0=token0,
        token_1=token1,
        start_at=start_at,
        end_at=end_at,
    )
    legacy_payload = _get_transactions_legacy(
        token_0=token0,
        token_1=token1,
        start_at=start_at,
        end_at=end_at,
    )
    rollout.compare(
        endpoint='/transactions',
        legacy_payload=legacy_payload,
        new_payload=payload,
    )
    return payload


@app.get('/transactions/start_at/{start_at}/end_at/{end_at}')
async def on_get_combined_transactions(start_at: int, end_at: int):
    rollout = _build_priority1_rollout()
    if rollout.use_legacy():
        return _get_transactions_legacy(
            token_0=None,
            token_1=None,
            start_at=start_at,
            end_at=end_at,
        )
    payload = _build_transactions_handler().get_transactions(
        token_0=None,
        token_1=None,
        start_at=start_at,
        end_at=end_at,
    )
    legacy_payload = _get_transactions_legacy(
        token_0=None,
        token_1=None,
        start_at=start_at,
        end_at=end_at,
    )
    rollout.compare(
        endpoint='/transactions/combined',
        legacy_payload=legacy_payload,
        new_payload=payload,
    )
    return payload


@app.get('/transactions/token0/{token0}/token1/{token1}/information')
async def on_get_transactions_information(token0: str, token1: str):
    try:
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            return _get_transactions_information_legacy(token_0=token0, token_1=token1)
        payload = _build_transactions_handler().get_information(token_0=token0, token_1=token1)
        legacy_payload = _get_transactions_information_legacy(token_0=token0, token_1=token1)
        rollout.compare(
            endpoint='/transactions/information',
            legacy_payload=legacy_payload,
            new_payload=payload,
        )
        return payload
    except Exception as e:
        print(f'Failed get transactions information: {e}')
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/transactions/information')
async def on_get_combined_transactions_information():
    try:
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            return _get_transactions_information_legacy(token_0=None, token_1=None)
        payload = _build_transactions_handler().get_information(token_0=None, token_1=None)
        legacy_payload = _get_transactions_information_legacy(token_0=None, token_1=None)
        rollout.compare(
            endpoint='/transactions/information/combined',
            legacy_payload=legacy_payload,
            new_payload=payload,
        )
        return payload
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
        rollout = _build_priority1_rollout()
        if rollout.use_legacy():
            return _get_positions_legacy(owner=owner, status=status)
        payload = _build_positions_handler().get_positions(owner=owner, status=status)
        legacy_payload = _get_positions_legacy(owner=owner, status=status)
        rollout.compare(
            endpoint='/positions',
            legacy_payload=legacy_payload,
            new_payload=payload,
            owner=owner,
            status=status,
        )
        return payload
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


@app.get('/position-metrics')
async def on_get_position_metrics(
    owner: str = Query(...),
    status: str = Query(default='active'),
):
    try:
        positions = _db.get_positions(owner=owner, status=status)
        metrics = []
        for position in positions:
            live_metrics = await _position_metrics_fetcher(position)
            if 'value_warning_codes' not in live_metrics:
                live_metrics['value_warning_codes'] = []
            if 'value_warning_message' not in live_metrics:
                live_metrics['value_warning_message'] = None
            for field_name in ('fee_amount0', 'fee_amount1', 'protocol_fee_amount0', 'protocol_fee_amount1'):
                if live_metrics.get(field_name) is None:
                    live_metrics[field_name] = '0'
            if (
                not bool(live_metrics.get('exact_fee_supported'))
                or bool(live_metrics.get('computation_blockers'))
                or bool(live_metrics.get('value_warning_codes'))
            ):
                _db.record_diagnostic_event(
                    source='position_metrics',
                    event_type='inexact_position_metrics',
                    severity='warning',
                    owner=position['owner'],
                    pool_application=position['pool_application'],
                    pool_id=position['pool_id'],
                    status=position['status'],
                    details={
                        'metrics_status': live_metrics.get('metrics_status'),
                        'exact_fee_supported': bool(live_metrics.get('exact_fee_supported')),
                        'exact_principal_supported': bool(live_metrics.get('exact_principal_supported')),
                        'computation_blockers': list(live_metrics.get('computation_blockers') or []),
                        'value_warning_codes': list(live_metrics.get('value_warning_codes') or []),
                    },
                )
            metrics.append({
                'pool_application': position['pool_application'],
                'pool_id': position['pool_id'],
                'token_0': position['token_0'],
                'token_1': position['token_1'],
                'owner': position['owner'],
                'status': position['status'],
                'current_liquidity': position['current_liquidity'],
                **live_metrics,
            })
        return {
            'owner': owner,
            'metrics': metrics,
        }
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


@app.get('/diagnostics')
async def on_get_diagnostics(
    source: str | None = Query(default=None),
    owner: str | None = Query(default=None),
    pool_application: str | None = Query(default=None),
    pool_id: int | None = Query(default=None),
    limit: int = Query(default=200),
):
    try:
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if limit <= 0:
            raise ValueError('limit must be positive')
        return {
            'diagnostics': _db.get_diagnostic_events(
                source=source,
                owner=owner,
                pool_application=pool_application,
                pool_id=pool_id,
                limit=limit,
            ),
        }
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
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if limit <= 0:
            raise ValueError('limit must be positive')

        return {
            'traces': _db.get_debug_traces(
                source=source,
                component=component,
                operation=operation,
                owner=owner,
                pool_application=pool_application,
                pool_id=pool_id,
                start_at=start_at,
                end_at=end_at,
                limit=limit,
            ),
        }
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


@app.get('/debug/pool')
async def on_get_debug_pool_bundle(
    pool_application: str = Query(...),
    pool_id: int = Query(...),
    owner: str | None = Query(default=None),
    transaction_limit: int = Query(default=1000),
    diagnostics_limit: int = Query(default=200),
    include_live_recent: bool = Query(default=False),
    recent_window: int = Query(default=5000),
):
    try:
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if transaction_limit <= 0 or diagnostics_limit <= 0:
            raise ValueError('limits must be positive')
        if recent_window <= 0:
            raise ValueError('recent_window must be positive')

        transactions = _db.get_pool_transaction_history(
            pool_application=pool_application,
            pool_id=pool_id,
        )
        if len(transactions) > transaction_limit:
            transactions = transactions[-transaction_limit:]

        liquidity_history = []
        if owner is not None:
            liquidity_history = _db.get_position_liquidity_history(
                owner=owner,
                pool_application=pool_application,
                pool_id=pool_id,
            )

        live_recent_audit = None
        if include_live_recent:
            live_recent_audit = await _build_recent_transaction_window_audit(
                pool_id=pool_id,
                pool_application=pool_application,
                recent_window=recent_window,
            )

        return {
            'pool_application': pool_application,
            'pool_id': pool_id,
            'owner': owner,
            'transaction_count': len(transactions),
            'transactions': transactions,
            'liquidity_history': liquidity_history,
            'gap_summary': _db.get_pool_transaction_gap_summary(
                pool_application=pool_application,
                pool_id=pool_id,
            ),
            'diagnostics': _db.get_diagnostic_events(
                pool_application=pool_application,
                pool_id=pool_id,
                owner=owner,
                limit=diagnostics_limit,
            ),
            'live_recent_audit': live_recent_audit,
        }
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

async def run_ticker_forever():
    global _ticker
    while _ticker is not None and _ticker.running():
        try:
            await _ticker.run()
        except Exception as e:
            print(f'Ticker quiting ... {e}')
            traceback.print_exc()
            await asyncio.sleep(10)


@app.on_event('startup')
async def on_startup():
    global _ticker, _ticker_task, _ticker_db
    if _swap is None or manager is None or _db_config is None:
        return
    if _ticker_task is not None:
        return

    _ticker_db = Db(
        _db_config['host'],
        _db_config['port'],
        _db_config['db_name'],
        _db_config['username'],
        _db_config['password'],
        False,
    )
    _ticker = Ticker(manager, _swap, _ticker_db)
    _ticker_task = asyncio.create_task(run_ticker_forever())


@app.on_event('shutdown')
async def on_shutdown():
    global _ticker_task
    if _ticker is not None:
        _ticker.stop()
    if _ticker_task is not None:
        await _ticker_task
        _ticker_task = None
    if _ticker_db is not None:
        _ticker_db.close()

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

    _db_config = {
        'host': args.database_host,
        'port': args.database_port,
        'db_name': args.database_name,
        'username': args.database_user,
        'password': args.database_password,
    }

    _db = Db(args.database_host, args.database_port, args.database_name, args.database_user, args.database_password, args.clean_kline)
    _swap = Swap(args.swap_host, args.swap_chain_id, args.swap_application_id, None, db=_db)
    manager = WebSocketManager(_swap, _db)

    uvicorn.run(app, host=args.host, port=args.port, ws_ping_interval=30, ws_ping_timeout=10)

    if _db is not None:
        _db.close()
