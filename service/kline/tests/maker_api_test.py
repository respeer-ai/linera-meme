import os
import sys
import tempfile
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


async_request_stub = types.ModuleType('async_request')


async def dummy_post(*_args, **_kwargs):
    raise AssertionError('async_request.post should be stubbed by the test when needed')


async def dummy_get(*_args, **_kwargs):
    raise AssertionError('async_request.get should be stubbed by the test when needed')


async_request_stub.post = dummy_post
async_request_stub.get = dummy_get
sys.modules['async_request'] = async_request_stub

db_stub = types.ModuleType('db')
db_stub.Db = object
sys.modules['db'] = db_stub

fastapi_stub = types.ModuleType('fastapi')


class DummyFastAPI:
    def get(self, *_args, **_kwargs):
        return lambda fn: fn

    def on_event(self, *_args, **_kwargs):
        return lambda fn: fn


def dummy_query(default=None, **_kwargs):
    return default


fastapi_stub.FastAPI = DummyFastAPI
fastapi_stub.Query = dummy_query
sys.modules['fastapi'] = fastapi_stub

fastapi_responses_stub = types.ModuleType('fastapi.responses')


class DummyJSONResponse:
    def __init__(self, status_code: int, content: dict):
        self.status_code = status_code
        self.content = content
        self.body = (
            '{'
            + ','.join(f'"{key}":"{value}"' for key, value in content.items())
            + '}'
        ).encode()


fastapi_responses_stub.JSONResponse = DummyJSONResponse
sys.modules['fastapi.responses'] = fastapi_responses_stub

uvicorn_stub = types.ModuleType('uvicorn')
sys.modules['uvicorn'] = uvicorn_stub


import maker_api as maker_api_module  # noqa: E402


class FakeResponse:
    def __init__(self, status_code=200, text=''):
        self.status_code = status_code
        self._text = text
        self.ok = 200 <= status_code < 300

    @property
    def text(self):
        return self._text

    def json(self):
        import json
        return json.loads(self._text)


class FakeDb:
    def __init__(self, pool_catalog=None, watermarks=None, maker_events=None, traces=None):
        self.pool_catalog = pool_catalog or []
        self.watermarks = watermarks or {}
        self.maker_events = maker_events or []
        self.traces = traces or []
        self.sql_history = []
        self.pools_table = 'pools'
        self.transactions_table = 'transactions'
        self.maker_events_table = 'maker_events'
        self.debug_traces_table = 'debug_traces'
        self.cursor_dict = self.FakeCursor(self)

    class FakeCursor:
        def __init__(self, outer):
            self.outer = outer
            self.last_sql = ''
            self.last_params = ()
            self._last_rows = []

        def execute(self, sql, params=()):
            self.last_sql = ' '.join(sql.split())
            self.last_params = params
            self.outer.sql_history.append((self.last_sql, params))
            self._last_rows = self._resolve_rows()

        def fetchall(self):
            return list(self._last_rows)

        def fetchone(self):
            if len(self._last_rows) == 0:
                return None
            return dict(self._last_rows[0])

        def _resolve_rows(self):
            if 'FROM pools' in self.last_sql:
                return list(self.outer.pool_catalog)
            if 'FROM maker_events' in self.last_sql and 'COUNT(*) AS count' not in self.last_sql:
                rows = list(self.outer.maker_events)
                if 'WHERE token_0 = %s' in self.last_sql:
                    token_0, token_1, start_at, end_at = self.last_params
                    rows = [
                        row for row in rows
                        if row.get('token_0') == token_0
                        and row.get('token_1') == token_1
                        and int(row.get('created_at') or 0) >= int(start_at)
                        and int(row.get('created_at') or 0) <= int(end_at)
                    ]
                elif 'WHERE created_at >= %s' in self.last_sql:
                    start_at, end_at = self.last_params
                    rows = [
                        row for row in rows
                        if int(row.get('created_at') or 0) >= int(start_at)
                        and int(row.get('created_at') or 0) <= int(end_at)
                    ]
                return list(rows)
            if 'FROM maker_events' in self.last_sql and 'COUNT(*) AS count' in self.last_sql:
                rows = list(self.outer.maker_events)
                if 'WHERE token_0 = %s' in self.last_sql:
                    token_0, token_1 = self.last_params
                    rows = [
                        row for row in rows
                        if row.get('token_0') == token_0
                        and row.get('token_1') == token_1
                    ]
                created_values = [int(row['created_at']) for row in rows if row.get('created_at') is not None]
                return [{
                    'count': len(rows),
                    'timestamp_begin': None if len(created_values) == 0 else max(created_values),
                    'timestamp_end': None if len(created_values) == 0 else min(created_values),
                }]
            if 'FROM debug_traces' in self.last_sql:
                rows = list(self.outer.traces)
                param_index = 0
                for clause, field in (
                    ('source = %s', 'source'),
                    ('component = %s', 'component'),
                    ('operation = %s', 'operation'),
                    ('owner = %s', 'owner'),
                    ('pool_application = %s', 'pool_application'),
                ):
                    if clause in self.last_sql:
                        rows = [row for row in rows if row.get(field) == self.last_params[param_index]]
                        param_index += 1
                if 'pool_id = %s' in self.last_sql:
                    rows = [row for row in rows if row.get('pool_id') == int(self.last_params[param_index])]
                    param_index += 1
                if 'created_at >= %s' in self.last_sql:
                    rows = [row for row in rows if int(row.get('created_at') or 0) >= int(self.last_params[param_index])]
                    param_index += 1
                if 'created_at <= %s' in self.last_sql:
                    rows = [row for row in rows if int(row.get('created_at') or 0) <= int(self.last_params[param_index])]
                    param_index += 1
                limit = int(self.last_params[-1]) if self.last_params else len(rows)
                return list(rows[:limit])
            if 'FROM settled_trades st' in self.last_sql:
                return [
                    {
                        'pool_id': pool_id,
                        'pool_application': f'{chain_id}:{owner}',
                        'created_at': payload[0],
                        'transaction_id': payload[1],
                        'token_reversed': payload[2],
                    }
                    for (pool_id, chain_id, owner), payload in self.outer.watermarks.items()
                ]
            return []

    def ensure_fresh_read_connection(self):
        return None


class MakerApiTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_db = maker_api_module._db
        self.original_config = dict(maker_api_module._config)
        self.original_get = maker_api_module.async_request.get
        self.original_post = maker_api_module.async_request.post

    async def asyncTearDown(self):
        maker_api_module._db = self.original_db
        maker_api_module._config.clear()
        maker_api_module._config.update(self.original_config)
        maker_api_module.async_request.get = self.original_get
        maker_api_module.async_request.post = self.original_post

    async def test_build_wallet_host_tolerates_malformed_template(self):
        maker_api_module._config.update({
            'wallet_host_template': 'maker-wallet-service-{index.maker-wallet-service}',
        })

        self.assertEqual(
            maker_api_module.build_wallet_host(2),
            'maker-wallet-service-2.maker-wallet-service',
        )

    async def test_build_wallet_host_strips_duplicate_suffix_and_trailing_brace(self):
        maker_api_module._config.update({
            'wallet_host_template': 'maker-wallet-service-{index}.maker-wallet-service.maker-wallet-service}',
        })

        self.assertEqual(
            maker_api_module.build_wallet_host(0),
            'maker-wallet-service-0.maker-wallet-service',
        )

    async def test_on_get_debug_wallets_returns_wallet_metrics_and_balances(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            state_path = os.path.join(tmpdir, 'MAKER_WALLET_CHAIN_OWNER.0')
            with open(state_path, 'w', encoding='utf-8') as f:
                f.write('chain-a\nowner-a\n')

            maker_api_module._config.update({
                'maker_replicas': 1,
                'shared_app_data_dir': tmpdir,
                'wallet_host_template': 'maker-wallet-service-{index}.maker-wallet-service',
                'wallet_rpc_port': 8080,
                'wallet_metrics_port': 8082,
                'wallet_memory_limit_bytes': 1000,
            })

            async def fake_get(url, **_kwargs):
                self.assertEqual(url, 'http://maker-wallet-service-0.maker-wallet-service:8082/metrics')
                return FakeResponse(
                    text='\n'.join([
                        '# HELP process_resident_memory_bytes Resident memory size in bytes.',
                        'process_resident_memory_bytes 900',
                        'process_open_fds 12',
                    ]),
                )

            async def fake_post(url, json, **_kwargs):
                self.assertEqual(url, 'http://maker-wallet-service-0.maker-wallet-service:8080')
                self.assertIn('balances', json['query'])
                return FakeResponse(
                    text='{"data":{"balances":{"chain-a":{"chainBalance":"0.75","ownerBalances":{"owner-a":"0.5"}}}}}'
                )

            maker_api_module.async_request.get = fake_get
            maker_api_module.async_request.post = fake_post

            response = await maker_api_module.on_get_debug_wallets(
                include_metrics=True,
                include_balances=True,
            )

        self.assertEqual(len(response['wallets']), 1)
        wallet = response['wallets'][0]
        self.assertEqual(wallet['chain_id'], 'chain-a')
        self.assertEqual(wallet['owner'], 'owner-a')
        self.assertEqual(wallet['health'], 'wallet_memory_high')
        self.assertEqual(wallet['balances']['total_balance'], 1.25)
        self.assertEqual(wallet['metrics']['summary']['resident_memory_bytes'], 900.0)
        self.assertTrue(wallet['metrics']['summary']['memory_high'])

    async def test_on_get_debug_pools_stall_marks_mutation_not_settled(self):
        maker_api_module._config.update({
            'maker_replicas': 0,
            'wallet_memory_limit_bytes': 0,
        })
        maker_api_module._db = FakeDb(
            pool_catalog=[{
                'pool_id': 1001,
                'pool_application': 'chain-x:pool-owner',
                'token_0': 'TOKEN0',
                'token_1': 'TOKEN1',
            }],
            watermarks={
                (1001, 'chain-x', 'pool-owner'): (1_000, 7, 0),
            },
            maker_events=[{
                'event_id': 1,
                'pool_id': 1001,
                'event_type': 'executed',
                'created_at': 4_000,
            }],
            traces=[{
                'trace_id': 9,
                'source': 'maker',
                'component': 'swap',
                'operation': 'swap',
                'pool_application': 'chain-x:pool-owner',
                'pool_id': 1001,
                'owner': 'wallet-owner',
                'created_at': 4_500,
            }],
        )

        original_now_ms = maker_api_module.now_ms
        maker_api_module.now_ms = lambda: 10_000
        try:
            response = await maker_api_module.on_get_debug_pools_stall(
                pool_id=None,
                owner=None,
                lookback_minutes=10,
                stall_seconds=2,
                include_wallets=False,
            )
        finally:
            maker_api_module.now_ms = original_now_ms

        self.assertEqual(len(response['stalled_pools']), 1)
        stalled_pool = response['stalled_pools'][0]
        self.assertEqual(stalled_pool['pool_id'], 1001)
        self.assertEqual(stalled_pool['suspected_stage'], 'mutation_accepted_but_not_settled')
        self.assertEqual(stalled_pool['latest_db_transaction']['transaction_id'], 7)
        self.assertEqual(stalled_pool['latest_wallet_trace']['trace_id'], 9)
        self.assertTrue(
            any(
                'FROM settled_trades st' in sql
                for sql, _params in maker_api_module._db.sql_history
            )
        )

    async def test_debug_pools_stall_uses_query_repository_boundaries(self):
        class GuardedDb:
            def close(self):
                return None

        class FakePoolCatalogQueryRepository:
            def get_pool_catalog(self):
                return [{
                    'pool_id': 1001,
                    'pool_application': 'chain-x:pool-owner',
                    'token_0': 'TOKEN0',
                    'token_1': 'TOKEN1',
                }]

        class FakeTransactionWatermarksQueryRepository:
            def get_latest_transaction_watermarks(self):
                return {
                    (1001, 'chain-x', 'pool-owner'): (1_000, 7, 0),
                }

        class FakeMakerEventsQueryRepository:
            def get_maker_events(self, **_kwargs):
                return [{
                    'event_id': 1,
                    'pool_id': 1001,
                    'event_type': 'executed',
                    'created_at': 4_000,
                }]

        class FakeDebugTracesQueryRepository:
            def get_debug_traces(self, **_kwargs):
                return [{
                    'trace_id': 9,
                    'source': 'maker',
                    'component': 'swap',
                    'operation': 'swap',
                    'pool_application': 'chain-x:pool-owner',
                    'pool_id': 1001,
                    'owner': 'wallet-owner',
                    'created_at': 4_500,
                }]

        class GuardedMakerApiRuntime(maker_api_module.MakerApiRuntime):
            def pool_catalog_query_repository(self):
                return FakePoolCatalogQueryRepository()

            def transaction_watermarks_query_repository(self):
                return FakeTransactionWatermarksQueryRepository()

            def maker_events_query_repository(self):
                return FakeMakerEventsQueryRepository()

            def debug_traces_query_repository(self):
                return FakeDebugTracesQueryRepository()

        runtime = GuardedMakerApiRuntime(
            db=GuardedDb(),
            config={
                'maker_replicas': 0,
                'wallet_memory_limit_bytes': 0,
            },
            request_client=types.SimpleNamespace(),
            clock_ms=lambda: 10_000,
        )

        response = await runtime.get_debug_pools_stall(
            pool_id=None,
            owner=None,
            lookback_minutes=10,
            stall_seconds=2,
            include_wallets=False,
        )

        self.assertEqual(len(response['stalled_pools']), 1)
        stalled_pool = response['stalled_pools'][0]
        self.assertEqual(stalled_pool['pool_id'], 1001)
        self.assertEqual(stalled_pool['suspected_stage'], 'mutation_accepted_but_not_settled')
        self.assertEqual(stalled_pool['latest_db_transaction']['transaction_id'], 7)
        self.assertEqual(stalled_pool['latest_wallet_trace']['trace_id'], 9)

    async def test_on_get_debug_traces_defaults_to_lightweight_response(self):
        maker_api_module._db = FakeDb(
            traces=[{
                'trace_id': 11,
                'source': 'maker',
                'component': 'swap',
                'operation': 'swap',
                'target': 'wallet_application_mutation',
                'owner': 'owner-a',
                'pool_application': 'chain-a:pool-a',
                'pool_id': 1001,
                'request_url': 'http://wallet',
                'request_payload': {'query': 'mutation { swap }'},
                'response_status': 200,
                'response_body': {'data': 'hash'},
                'error': None,
                'details': {'token_0': 'A'},
                'created_at': 1234,
            }],
        )

        response = await maker_api_module.on_get_debug_traces(limit=10)

        self.assertEqual(len(response['traces']), 1)
        trace = response['traces'][0]
        self.assertEqual(trace['trace_id'], 11)
        self.assertIsNone(trace['request_payload'])
        self.assertIsNone(trace['response_body'])
        self.assertIsNone(trace['details'])

    async def test_on_get_maker_events_reads_projection_query_repo_shape(self):
        maker_api_module._db = FakeDb(
            maker_events=[{
                'event_id': 3,
                'source': 'maker',
                'event_type': 'executed',
                'pool_id': 1001,
                'token_0': 'AAA',
                'token_1': 'BBB',
                'amount_0': '1.25',
                'amount_1': '7.5',
                'quote_notional': '9.0',
                'pool_price': '7.2',
                'details': '{"side":"sell"}',
                'created_at': 1234,
            }],
        )

        response = await maker_api_module.on_get_maker_events(
            token0='AAA',
            token1='BBB',
            start_at=1000,
            end_at=2000,
        )

        self.assertEqual(len(response), 1)
        self.assertEqual(response[0]['event_id'], 3)
        self.assertEqual(response[0]['details']['side'], 'sell')

    async def test_on_get_maker_events_information_reads_projection_query_repo_shape(self):
        maker_api_module._db = FakeDb(
            maker_events=[
                {
                    'event_id': 1,
                    'source': 'maker',
                    'event_type': 'queued',
                    'pool_id': 1001,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'amount_0': '1',
                    'amount_1': None,
                    'quote_notional': '2',
                    'pool_price': '2',
                    'details': None,
                    'created_at': 1200,
                },
                {
                    'event_id': 2,
                    'source': 'maker',
                    'event_type': 'executed',
                    'pool_id': 1001,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'amount_0': '3',
                    'amount_1': None,
                    'quote_notional': '4',
                    'pool_price': '4',
                    'details': None,
                    'created_at': 1800,
                },
            ],
        )

        response = await maker_api_module.on_get_maker_events_information(
            token0='AAA',
            token1='BBB',
        )

        self.assertEqual(response['count'], 2)
        self.assertEqual(response['timestamp_begin'], 1800)
        self.assertEqual(response['timestamp_end'], 1200)

    async def test_on_get_debug_wallet_block_queries_specific_wallet(self):
        maker_api_module._config.update({
            'maker_replicas': 3,
            'wallet_host_template': 'maker-wallet-service-{index}.maker-wallet-service',
            'wallet_rpc_port': 8080,
        })

        async def fake_post(url, json, **_kwargs):
            self.assertEqual(url, 'http://maker-wallet-service-1.maker-wallet-service:8080')
            self.assertIn('block(chainId: "chain-a", hash: "hash-a")', json['query'])
            return FakeResponse(
                text='{"data":{"block":{"hash":"hash-a","status":"confirmed","block":{"header":{"chainId":"chain-a","height":"7","timestamp":123,"previousBlockHash":"prev"},"body":{"messages":[]}}}}}'
            )

        maker_api_module.async_request.post = fake_post

        response = await maker_api_module.on_get_debug_wallet_block(
            index=1,
            chain_id='chain-a',
            block_hash='hash-a',
        )

        self.assertEqual(response['index'], 1)
        self.assertEqual(response['result']['reachable'], True)
        self.assertEqual(response['result']['block']['hash'], 'hash-a')
        self.assertEqual(response['result']['block']['status'], 'confirmed')

    async def test_on_get_debug_wallet_pending_messages_queries_specific_wallet(self):
        maker_api_module._config.update({
            'maker_replicas': 3,
            'wallet_host_template': 'maker-wallet-service-{index}.maker-wallet-service',
            'wallet_rpc_port': 8080,
        })

        async def fake_post(url, json, **_kwargs):
            self.assertEqual(url, 'http://maker-wallet-service-2.maker-wallet-service:8080')
            self.assertIn('pendingMessages(chainId: "chain-pool")', json['query'])
            return FakeResponse(
                text='{"data":{"pendingMessages":[{"action":"Accept","origin":"chain-src","bundle":{"certificateHash":"hash-b","height":"9","timestamp":456,"transactionIndex":0}}]}}'
            )

        maker_api_module.async_request.post = fake_post

        response = await maker_api_module.on_get_debug_wallet_pending_messages(
            index=2,
            chain_id='chain-pool',
        )

        self.assertEqual(response['index'], 2)
        self.assertEqual(response['result']['reachable'], True)
        self.assertEqual(len(response['result']['pending_messages']), 1)
        self.assertEqual(response['result']['pending_messages'][0]['bundle']['certificateHash'], 'hash-b')
