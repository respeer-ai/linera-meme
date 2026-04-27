from contextlib import asynccontextmanager
from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import argparse
import os
import re
import time
import uvicorn

import async_request
from db import Db
from maker_runtime import MakerRuntime

_db = None
_config = {
    'maker_replicas': 1,
    'shared_app_data_dir': '/shared-app-data',
    'wallet_host_template': 'maker-wallet-service-{index}.maker-wallet-service',
    'wallet_rpc_port': 8080,
    'wallet_metrics_port': 8082,
    'wallet_memory_limit_bytes': 0,
    'swap_host': None,
    'swap_chain_id': None,
    'swap_application_id': None,
    'wallet_host': None,
    'wallet_owner': None,
    'wallet_chain': None,
    'proxy_host': None,
    'proxy_chain_id': None,
    'proxy_application_id': None,
    'faucet_url': 'https://faucet.testnet-conway.linera.net',
    'database_host': None,
    'database_port': None,
    'database_user': None,
    'database_password': None,
    'database_name': None,
}
_runtime = None


def now_ms() -> int:
    return int(time.time() * 1000)


def build_trader_runtime_status() -> dict:
    if _runtime is None:
        return {
            'enabled': False,
            'running': False,
            'started_at_ms': None,
            'last_iteration_started_at_ms': None,
            'last_iteration_finished_at_ms': None,
            'last_sleep_seconds': None,
            'last_trade_duration_ms': None,
            'last_error': None,
            'last_error_at_ms': None,
            'consecutive_failures': 0,
            'iterations': 0,
            'cycle': None,
        }
    return _runtime.status()


@asynccontextmanager
async def app_lifespan(_app):
    global _runtime

    _runtime = MakerRuntime(now_ms=now_ms, config=_config)
    _runtime.start()
    try:
        yield
    finally:
        if _runtime is not None:
            _runtime.stop()
            _runtime = None

        global _db
        if _db is not None:
            _db.close()
            _db = None


app = FastAPI(lifespan=app_lifespan)


def build_wallet_host(index: int) -> str:
    template = str(_config.get('wallet_host_template') or '').strip()
    if template == '':
        return f'maker-wallet-service-{index}.maker-wallet-service'

    for placeholder in ('{index}', '${index}', '{{index}}'):
        if placeholder in template:
            return template.replace(placeholder, str(index))

    malformed_match = re.match(r'^(.*)\{index(?:\.([^}]+))?\}(.*)$', template)
    if malformed_match is not None:
        prefix, embedded_suffix, trailing_suffix = malformed_match.groups()
        suffix = trailing_suffix
        if embedded_suffix:
            suffix = embedded_suffix if embedded_suffix.startswith(('.', ':', '/')) else f'.{embedded_suffix}'
            suffix += trailing_suffix
        return f'{prefix}{index}{suffix}'

    try:
        return template.format(index=index)
    except Exception:
        return template


def build_wallet_rpc_url(index: int) -> str:
    return f'http://{build_wallet_host(index)}:{_config["wallet_rpc_port"]}'


def build_wallet_metrics_url(index: int) -> str:
    return f'http://{build_wallet_host(index)}:{_config["wallet_metrics_port"]}/metrics'


def load_wallet_descriptor(index: int):
    path = os.path.join(
        _config['shared_app_data_dir'],
        f'MAKER_WALLET_CHAIN_OWNER.{index}',
    )
    descriptor = {
        'index': index,
        'state_path': path,
        'state_file_exists': os.path.exists(path),
        'chain_id': None,
        'owner': None,
    }
    if descriptor['state_file_exists'] is not True:
        return descriptor

    with open(path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]

    if len(lines) >= 1:
        descriptor['chain_id'] = lines[0]
    if len(lines) >= 2:
        descriptor['owner'] = lines[1]
    return descriptor


def parse_prometheus_metrics(body: str):
    metrics = {}
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line == '' or line.startswith('#'):
            continue

        parts = line.split()
        if len(parts) < 2:
            continue

        raw_name = parts[0]
        metric_name = raw_name.split('{', 1)[0]

        try:
            metrics[metric_name] = float(parts[-1])
        except ValueError:
            continue
    return metrics


def summarize_wallet_metrics(metrics: dict):
    resident_memory_bytes = metrics.get('process_resident_memory_bytes')
    virtual_memory_bytes = metrics.get('process_virtual_memory_bytes')
    memory_limit_bytes = int(_config.get('wallet_memory_limit_bytes') or 0)
    resident_memory_ratio = None
    memory_high = False

    if resident_memory_bytes is not None and memory_limit_bytes > 0:
        resident_memory_ratio = resident_memory_bytes / memory_limit_bytes
        memory_high = resident_memory_ratio >= 0.85

    selected_metrics = {}
    for key in sorted(metrics.keys()):
        lowered = key.lower()
        if (
            lowered.startswith('process_')
            or 'memory' in lowered
            or 'listener' in lowered
            or 'queue' in lowered
            or 'pending' in lowered
            or 'sync' in lowered
            or 'certificate' in lowered
            or 'inbox' in lowered
            or 'outbox' in lowered
        ):
            selected_metrics[key] = metrics[key]

    return {
        'metric_count': len(metrics),
        'resident_memory_bytes': resident_memory_bytes,
        'resident_memory_mib': None if resident_memory_bytes is None else round(resident_memory_bytes / 1024 / 1024, 2),
        'virtual_memory_bytes': virtual_memory_bytes,
        'virtual_memory_mib': None if virtual_memory_bytes is None else round(virtual_memory_bytes / 1024 / 1024, 2),
        'open_fds': metrics.get('process_open_fds'),
        'start_time_seconds': metrics.get('process_start_time_seconds'),
        'wallet_memory_limit_bytes': memory_limit_bytes if memory_limit_bytes > 0 else None,
        'resident_memory_ratio': None if resident_memory_ratio is None else round(resident_memory_ratio, 4),
        'memory_high': memory_high,
        'selected_metrics': selected_metrics,
    }


async def fetch_wallet_metrics(index: int):
    url = build_wallet_metrics_url(index)
    try:
        response = await async_request.get(url=url, timeout=(2, 5))
        if response.ok is not True:
            return {
                'reachable': False,
                'status_code': response.status_code,
                'error': f'HTTP {response.status_code}',
                'metrics_url': url,
            }

        metrics = parse_prometheus_metrics(response.text)
        return {
            'reachable': True,
            'status_code': response.status_code,
            'metrics_url': url,
            'summary': summarize_wallet_metrics(metrics),
        }
    except Exception as e:
        return {
            'reachable': False,
            'status_code': None,
            'error': str(e),
            'metrics_url': url,
        }


async def fetch_wallet_balances(index: int, descriptor: dict):
    if descriptor.get('chain_id') is None or descriptor.get('owner') is None:
        return {
            'reachable': False,
            'error': 'wallet chain/owner metadata is unavailable',
        }

    chain_id = descriptor['chain_id']
    owner = descriptor['owner']
    payload = {
        'query': f'query {{\n balances(chainOwners:[{{chainId: "{chain_id}", owners: ["{owner}"]}}]) \n}}'
    }
    url = build_wallet_rpc_url(index)

    try:
        response = await async_request.post(url=url, json=payload, timeout=(3, 10))
        payload_json = response.json() if response.text else {}
        if response.ok is not True:
            return {
                'reachable': False,
                'status_code': response.status_code,
                'error': f'HTTP {response.status_code}',
                'wallet_url': url,
            }
        if 'errors' in payload_json:
            return {
                'reachable': False,
                'status_code': response.status_code,
                'error': payload_json['errors'],
                'wallet_url': url,
            }

        balances = payload_json.get('data', {}).get('balances', {})
        chain_balances = balances.get(chain_id, {})
        owner_balances = chain_balances.get('ownerBalances', {})
        chain_balance = float(chain_balances.get('chainBalance', 0))
        owner_balance = float(owner_balances.get(owner, 0))
        return {
            'reachable': True,
            'status_code': response.status_code,
            'wallet_url': url,
            'chain_id': chain_id,
            'owner': owner,
            'chain_balance': chain_balance,
            'owner_balance': owner_balance,
            'total_balance': chain_balance + owner_balance,
        }
    except Exception as e:
        return {
            'reachable': False,
            'status_code': None,
            'error': str(e),
            'wallet_url': url,
        }


def build_wallet_health(metrics_result, balances_result):
    if metrics_result is not None and metrics_result.get('reachable') is not True:
        return 'wallet_metrics_unreachable'

    if balances_result is not None:
        if balances_result.get('reachable') is not True:
            return 'wallet_balance_unreachable'
        if balances_result.get('total_balance', 0) < 0.001:
            return 'wallet_low_gas'

    if metrics_result is not None:
        summary = metrics_result.get('summary', {})
        if summary.get('memory_high') is True:
            return 'wallet_memory_high'

    return 'ok'


async def build_wallet_snapshot(index: int, include_metrics: bool, include_balances: bool):
    descriptor = load_wallet_descriptor(index)
    metrics_result = await fetch_wallet_metrics(index) if include_metrics else None
    balances_result = await fetch_wallet_balances(index, descriptor) if include_balances else None

    return {
        'index': index,
        'rpc_url': build_wallet_rpc_url(index),
        'metrics_url': build_wallet_metrics_url(index),
        'chain_id': descriptor.get('chain_id'),
        'owner': descriptor.get('owner'),
        'state_path': descriptor.get('state_path'),
        'state_file_exists': descriptor.get('state_file_exists'),
        'health': build_wallet_health(metrics_result, balances_result),
        'metrics': metrics_result,
        'balances': balances_result,
    }


async def build_wallet_index(include_metrics: bool, include_balances: bool):
    wallets = []
    for index in range(int(_config['maker_replicas'])):
        wallets.append(await build_wallet_snapshot(
            index=index,
            include_metrics=include_metrics,
            include_balances=include_balances,
        ))
    return wallets


def group_latest_by(rows: list, key_builder):
    latest = {}
    for row in rows:
        key = key_builder(row)
        if key is None:
            continue
        created_at = int(row.get('created_at') or 0)
        current = latest.get(key)
        if current is None or created_at >= int(current.get('created_at') or 0):
            latest[key] = row
    return latest


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


@app.get('/debug/wallets')
async def on_get_debug_wallets(
    include_metrics: bool = Query(default=True),
    include_balances: bool = Query(default=True),
):
    try:
        return {
            'wallets': await build_wallet_index(
                include_metrics=include_metrics,
                include_balances=include_balances,
            ),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/wallets/{index}/metrics')
async def on_get_debug_wallet_metrics(index: int):
    try:
        if index < 0 or index >= int(_config['maker_replicas']):
            raise ValueError('wallet index out of range')

        descriptor = load_wallet_descriptor(index)
        return {
            'index': index,
            'chain_id': descriptor.get('chain_id'),
            'owner': descriptor.get('owner'),
            'metrics': await fetch_wallet_metrics(index),
        }
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


@app.get('/debug/wallets/{index}/balances')
async def on_get_debug_wallet_balances(index: int):
    try:
        if index < 0 or index >= int(_config['maker_replicas']):
            raise ValueError('wallet index out of range')

        descriptor = load_wallet_descriptor(index)
        return {
            'index': index,
            'balances': await fetch_wallet_balances(index, descriptor),
        }
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
    include_storage: bool = Query(default=False),
):
    try:
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if limit <= 0:
            raise ValueError('limit must be positive')

        response = {
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
                include_payloads=include_payloads,
            ),
        }
        if include_storage:
            response['storage'] = _db.get_debug_trace_storage_status()
        return response
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


@app.get('/debug/storage')
async def on_get_debug_storage():
    try:
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        return {
            'debug_traces': _db.get_debug_trace_storage_status(),
        }
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
        if _db is None:
            raise RuntimeError('Db client is not initialized')
        if lookback_minutes <= 0:
            raise ValueError('lookback_minutes must be positive')
        if stall_seconds <= 0:
            raise ValueError('stall_seconds must be positive')

        current_ms = now_ms()
        start_at = current_ms - lookback_minutes * 60 * 1000
        pool_catalog = _db.get_pool_catalog()
        if pool_id is not None:
            pool_catalog = [row for row in pool_catalog if int(row['pool_id']) == int(pool_id)]

        latest_watermarks = _db.get_latest_transaction_watermarks()
        maker_events = _db.get_maker_events(token_0=None, token_1=None, start_at=start_at, end_at=current_ms)
        if pool_id is not None:
            maker_events = [row for row in maker_events if int(row['pool_id']) == int(pool_id)]

        traces = _db.get_debug_traces(
            source='maker',
            component='swap',
            operation='swap',
            owner=owner,
            pool_id=pool_id,
            start_at=start_at,
            end_at=current_ms,
            limit=1000,
        )

        latest_events_by_pool = group_latest_by(
            maker_events,
            key_builder=lambda row: int(row['pool_id']) if row.get('pool_id') is not None else None,
        )
        latest_traces_by_pool = group_latest_by(
            traces,
            key_builder=lambda row: (row.get('pool_application'), int(row['pool_id'])) if row.get('pool_application') is not None and row.get('pool_id') is not None else None,
        )

        wallet_snapshots = await build_wallet_index(
            include_metrics=include_wallets,
            include_balances=include_wallets,
        ) if include_wallets else []
        wallet_by_owner = {
            row['owner']: row
            for row in wallet_snapshots
            if row.get('owner') is not None
        }

        stalled_pools = []
        for pool in pool_catalog:
            pool_application = pool['pool_application']
            pool_key_parts = pool_application.split(':', 1)
            if len(pool_key_parts) != 2:
                continue

            latest_tx = latest_watermarks.get((pool['pool_id'], pool_key_parts[0], pool_key_parts[1]))
            latest_event = latest_events_by_pool.get(pool['pool_id'])
            latest_trace = latest_traces_by_pool.get((pool_application, pool['pool_id']))
            latest_trace_owner = latest_trace.get('owner') if latest_trace is not None else None
            wallet_snapshot = wallet_by_owner.get(latest_trace_owner)

            latest_tx_created_at = None if latest_tx is None else int(latest_tx[0])
            latest_event_created_at = None if latest_event is None else int(latest_event['created_at'])
            latest_trace_created_at = None if latest_trace is None else int(latest_trace['created_at'])

            latest_upstream_created_at = max([
                value for value in [latest_event_created_at, latest_trace_created_at]
                if value is not None
            ], default=None)

            suspected_stage = 'unknown'
            lag_seconds = None
            if latest_upstream_created_at is None:
                suspected_stage = 'maker_idle'
                if latest_tx_created_at is not None:
                    lag_seconds = round((current_ms - latest_tx_created_at) / 1000, 3)
            else:
                baseline_created_at = latest_tx_created_at if latest_tx_created_at is not None else 0
                lag_seconds = round((latest_upstream_created_at - baseline_created_at) / 1000, 3)
                if latest_trace is not None and latest_tx_created_at is not None and latest_trace_created_at <= latest_tx_created_at + stall_seconds * 1000:
                    suspected_stage = 'settled'
                elif wallet_snapshot is not None and wallet_snapshot.get('health') == 'wallet_metrics_unreachable':
                    suspected_stage = 'wallet_metrics_unreachable'
                elif wallet_snapshot is not None and wallet_snapshot.get('health') == 'wallet_low_gas':
                    suspected_stage = 'wallet_low_gas'
                elif wallet_snapshot is not None and wallet_snapshot.get('health') == 'wallet_memory_high':
                    suspected_stage = 'wallet_memory_high'
                else:
                    suspected_stage = 'mutation_accepted_but_not_settled'

            if latest_upstream_created_at is None and latest_tx_created_at is not None:
                should_include = (current_ms - latest_tx_created_at) >= stall_seconds * 1000
            elif latest_upstream_created_at is None:
                should_include = False
            elif latest_tx_created_at is None:
                should_include = True
            else:
                should_include = latest_upstream_created_at > latest_tx_created_at + stall_seconds * 1000

            if should_include is not True:
                continue

            stalled_pools.append({
                'pool_id': pool['pool_id'],
                'pool_application': pool_application,
                'token_0': pool['token_0'],
                'token_1': pool['token_1'],
                'lag_seconds': lag_seconds,
                'suspected_stage': suspected_stage,
                'latest_db_transaction': None if latest_tx is None else {
                    'created_at': latest_tx_created_at,
                    'transaction_id': int(latest_tx[1]),
                    'token_reversed': int(latest_tx[2]),
                },
                'latest_maker_event': latest_event,
                'latest_wallet_trace': latest_trace,
                'wallet': wallet_snapshot,
            })

        stalled_pools.sort(
            key=lambda row: (
                -(row['lag_seconds'] or 0),
                row['pool_id'],
            )
        )

        return {
            'generated_at': current_ms,
            'lookback_minutes': lookback_minutes,
            'stall_seconds': stall_seconds,
            'stalled_pools': stalled_pools,
            'wallets': wallet_snapshots if include_wallets else None,
        }
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
        if _db is None:
            raise RuntimeError('Db client is not initialized')

        wallets = await build_wallet_index(include_metrics=False, include_balances=False)
        return {
            'status': 'ok',
            'generated_at': now_ms(),
            'maker_replicas': int(_config['maker_replicas']),
            'wallet_state_files_found': len([row for row in wallets if row['state_file_exists'] is True]),
            'trader': build_trader_runtime_status(),
            'wallets': wallets,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


@app.get('/debug/trader')
async def on_get_debug_trader():
    try:
        return build_trader_runtime_status()
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Linera Maker API')

    parser.add_argument('--host', type=str, default='0.0.0.0', help='Listened ip')
    parser.add_argument('--port', type=int, default=8080, help='Listened port')
    parser.add_argument('--database-host', type=str, default='localhost', help='Maker database host')
    parser.add_argument('--database-port', type=str, default='3306', help='Maker database port')
    parser.add_argument('--database-user', type=str, default='debian-sys-maint ', help='Maker database user')
    parser.add_argument('--database-password', type=str, default='4EwQJrNprvw8McZm', help='Maker database password')
    parser.add_argument('--database-name', type=str, default='linera_swap_kline', help='Maker database name')
    parser.add_argument('--maker-replicas', type=int, default=1, help='Maker wallet replicas')
    parser.add_argument('--shared-app-data-dir', type=str, default='/shared-app-data', help='Path of shared app data')
    parser.add_argument('--wallet-host-template', type=str, default='maker-wallet-service-{index}.maker-wallet-service', help='Maker wallet host template')
    parser.add_argument('--wallet-rpc-port', type=int, default=8080, help='Maker wallet rpc port')
    parser.add_argument('--wallet-metrics-port', type=int, default=8082, help='Maker wallet metrics port')
    parser.add_argument('--wallet-memory-limit-bytes', type=int, default=0, help='Maker wallet memory limit')
    parser.add_argument('--swap-host', type=str, default='', help='Host of swap service')
    parser.add_argument('--swap-chain-id', type=str, default='', help='Swap chain id')
    parser.add_argument('--swap-application-id', type=str, default='', help='Swap application id')
    parser.add_argument('--wallet-host', type=str, default='', help='Host of wallet service')
    parser.add_argument('--wallet-owner', type=str, default='', help='Owner of wallet')
    parser.add_argument('--wallet-chain', type=str, default='', help='Chain of wallet')
    parser.add_argument('--proxy-host', type=str, default='', help='Host of proxy service')
    parser.add_argument('--proxy-chain-id', type=str, default='', help='Proxy chain id')
    parser.add_argument('--proxy-application-id', type=str, default='', help='Proxy application id')
    parser.add_argument('--faucet-url', type=str, default='https://faucet.testnet-conway.linera.net', help='Faucet url')

    args = parser.parse_args()

    _config['maker_replicas'] = max(int(args.maker_replicas), 0)
    _config['shared_app_data_dir'] = args.shared_app_data_dir
    _config['wallet_host_template'] = args.wallet_host_template
    _config['wallet_rpc_port'] = int(args.wallet_rpc_port)
    _config['wallet_metrics_port'] = int(args.wallet_metrics_port)
    _config['wallet_memory_limit_bytes'] = int(args.wallet_memory_limit_bytes)
    _config['swap_host'] = args.swap_host
    _config['swap_chain_id'] = args.swap_chain_id
    _config['swap_application_id'] = args.swap_application_id
    _config['wallet_host'] = args.wallet_host
    _config['wallet_owner'] = args.wallet_owner
    _config['wallet_chain'] = args.wallet_chain
    _config['proxy_host'] = args.proxy_host
    _config['proxy_chain_id'] = args.proxy_chain_id
    _config['proxy_application_id'] = args.proxy_application_id
    _config['faucet_url'] = args.faucet_url
    _config['database_host'] = args.database_host
    _config['database_port'] = args.database_port
    _config['database_user'] = args.database_user
    _config['database_password'] = args.database_password
    _config['database_name'] = args.database_name

    _db = Db(
        args.database_host,
        args.database_port,
        args.database_name,
        args.database_user,
        args.database_password,
        False,
    )

    uvicorn.run(app, host=args.host, port=args.port, ws_ping_interval=30, ws_ping_timeout=10)
