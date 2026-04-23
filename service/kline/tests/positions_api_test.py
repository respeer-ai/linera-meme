import sys
import types
import unittest
import os
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


swap_stub = sys.modules.get('swap', types.ModuleType('swap'))
swap_stub.Swap = getattr(swap_stub, 'Swap', object)
swap_stub.Transaction = getattr(swap_stub, 'Transaction', object)
swap_stub.Pool = getattr(swap_stub, 'Pool', object)
sys.modules['swap'] = swap_stub

subscription_stub = types.ModuleType('subscription')
subscription_stub.WebSocketManager = object
sys.modules['subscription'] = subscription_stub

ticker_stub = types.ModuleType('ticker')
ticker_stub.Ticker = object
sys.modules['ticker'] = ticker_stub

async_request_stub = types.ModuleType('async_request')

async def dummy_post(*_args, **_kwargs):
    raise AssertionError('async_request.post should be stubbed by the test when needed')

async_request_stub.post = dummy_post
sys.modules['async_request'] = async_request_stub

db_stub = types.ModuleType('db')
db_stub.Db = object
db_stub.align_timestamp_to_minute_ms = lambda value: value
sys.modules['db'] = db_stub

fastapi_stub = types.ModuleType('fastapi')


class DummyFastAPI:
    def get(self, *_args, **_kwargs):
        return lambda fn: fn

    def post(self, *_args, **_kwargs):
        return lambda fn: fn

    def websocket(self, *_args, **_kwargs):
        return lambda fn: fn

    def on_event(self, *_args, **_kwargs):
        return lambda fn: fn


def dummy_query(default=None, **_kwargs):
    return default


fastapi_stub.FastAPI = DummyFastAPI
fastapi_stub.Query = dummy_query
fastapi_stub.Request = object
fastapi_stub.WebSocket = object
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


import kline as kline_module  # noqa: E402


class FakeDb:
    def __init__(self, positions=None, error=None):
        self.positions = positions or []
        self.error = error
        self.calls = []
        self.transaction_ids = []
        self.diagnostics = []
        self.debug_traces = []
        self.gap_summary = {
            'has_internal_gaps': False,
            'start_id': None,
            'end_id': None,
            'missing_count': 0,
            'missing_ids_sample': [],
        }

    def get_positions(self, owner: str, status: str):
        self.calls.append({'owner': owner, 'status': status})
        if self.error is not None:
            raise self.error
        return self.positions

    def get_pool_transaction_ids(self, pool_id: int, pool_application: str, start_id: int, end_id: int):
        self.calls.append({
            'pool_id': pool_id,
            'pool_application': pool_application,
            'start_id': start_id,
            'end_id': end_id,
        })
        if self.error is not None:
            raise self.error
        return list(self.transaction_ids)

    def get_pool_transaction_history(self, pool_application: str, pool_id: int):
        self.calls.append({
            'pool_application': pool_application,
            'pool_id': pool_id,
            'history': True,
        })
        if self.error is not None:
            raise self.error
        return list(self.positions)

    def get_position_liquidity_history(self, owner: str, pool_application: str, pool_id: int):
        self.calls.append({
            'owner': owner,
            'pool_application': pool_application,
            'pool_id': pool_id,
            'liquidity_history': True,
        })
        if self.error is not None:
            raise self.error
        return list(self.positions)

    def get_pool_transaction_gap_summary(self, pool_application: str, pool_id: int):
        self.calls.append({
            'pool_application': pool_application,
            'pool_id': pool_id,
            'gap_summary': True,
        })
        if self.error is not None:
            raise self.error
        return dict(self.gap_summary)

    def record_diagnostic_event(self, **kwargs):
        self.diagnostics.append(dict(kwargs))

    def get_diagnostic_events(self, *, source=None, owner=None, pool_application=None, pool_id=None, limit=200):
        rows = list(self.diagnostics)
        if source is not None:
            rows = [row for row in rows if row.get('source') == source]
        if owner is not None:
            rows = [row for row in rows if row.get('owner') == owner]
        if pool_application is not None:
            rows = [row for row in rows if row.get('pool_application') == pool_application]
        if pool_id is not None:
            rows = [row for row in rows if row.get('pool_id') == pool_id]
        return rows[:limit]

    def get_debug_traces(
        self,
        *,
        source=None,
        component=None,
        operation=None,
        owner=None,
        pool_application=None,
        pool_id=None,
        start_at=None,
        end_at=None,
        limit=200,
    ):
        rows = list(self.debug_traces)
        if source is not None:
            rows = [row for row in rows if row.get('source') == source]
        if component is not None:
            rows = [row for row in rows if row.get('component') == component]
        if operation is not None:
            rows = [row for row in rows if row.get('operation') == operation]
        if owner is not None:
            rows = [row for row in rows if row.get('owner') == owner]
        if pool_application is not None:
            rows = [row for row in rows if row.get('pool_application') == pool_application]
        if pool_id is not None:
            rows = [row for row in rows if row.get('pool_id') == pool_id]
        if start_at is not None:
            rows = [row for row in rows if row.get('created_at') is not None and row.get('created_at') >= start_at]
        if end_at is not None:
            rows = [row for row in rows if row.get('created_at') is not None and row.get('created_at') <= end_at]
        return rows[:limit]


class FakeRawRepository:
    def __init__(self):
        self.calls = []
        self.cursors = []
        self.runs = []
        self.anomalies = []

    def list_chain_cursors(self, *, chain_ids=(), limit=200):
        self.calls.append(('list_chain_cursors', chain_ids, limit))
        return list(self.cursors)

    def list_recent_ingest_runs(self, *, chain_ids=(), statuses=(), limit=200):
        self.calls.append(('list_recent_ingest_runs', chain_ids, statuses, limit))
        return list(self.runs)

    def list_ingestion_anomalies(self, *, chain_ids=(), statuses=(), limit=200):
        self.calls.append(('list_ingestion_anomalies', chain_ids, statuses, limit))
        return list(self.anomalies)


class PositionsApiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.original_rollout_mode = os.environ.get('KLINE_PRIORITY1_ROLLOUT_MODE')
        self.original_parity = os.environ.get('KLINE_PRIORITY1_PARITY')
        os.environ.pop('KLINE_PRIORITY1_ROLLOUT_MODE', None)
        os.environ.pop('KLINE_PRIORITY1_PARITY', None)

    def tearDown(self):
        if self.original_rollout_mode is None:
            os.environ.pop('KLINE_PRIORITY1_ROLLOUT_MODE', None)
        else:
            os.environ['KLINE_PRIORITY1_ROLLOUT_MODE'] = self.original_rollout_mode
        if self.original_parity is None:
            os.environ.pop('KLINE_PRIORITY1_PARITY', None)
        else:
            os.environ['KLINE_PRIORITY1_PARITY'] = self.original_parity

    async def test_on_get_positions_returns_owner_and_positions(self):
        original_db = kline_module._db
        fake_db = FakeDb(positions=[
            {'pool_id': 7, 'status': 'active'},
        ])
        kline_module._db = fake_db

        try:
            response = await kline_module.on_get_positions(owner='chain:owner-a', status='active')
        finally:
            kline_module._db = original_db

        self.assertEqual(response, {
            'owner': 'chain:owner-a',
            'positions': [{'pool_id': 7, 'status': 'active'}],
        })
        self.assertEqual(fake_db.calls[0], {'owner': 'chain:owner-a', 'status': 'active'})

    async def test_on_get_positions_returns_400_for_invalid_status(self):
        original_db = kline_module._db
        fake_db = FakeDb(error=ValueError('Invalid positions status'))
        kline_module._db = fake_db

        try:
            response = await kline_module.on_get_positions(owner='chain:owner-a', status='bad')
        finally:
            kline_module._db = original_db

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, b'{"error":"Invalid positions status"}')

    async def test_on_get_position_metrics_returns_live_metrics(self):
        original_db = kline_module._db
        original_fetcher = kline_module._position_metrics_fetcher
        fake_db = FakeDb(positions=[
            {
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'token_0': 'QQQ',
                'token_1': 'TLINERA',
                'owner': 'chain:owner-a',
                'status': 'active',
                'current_liquidity': '0.346087',
            },
        ])

        async def fake_fetcher(position):
            self.assertEqual(position['pool_id'], 7)
            return {
                'position_liquidity_live': '0.346087',
                'total_supply_live': '1.000000',
                'exact_share_ratio': '0.346087',
                'redeemable_amount0': '123.45',
                'redeemable_amount1': '6.78',
                'virtual_initial_liquidity': True,
                'metrics_status': 'partial_live_redeemable_only',
                'exact_fee_supported': False,
                'exact_principal_supported': False,
                'owner_is_fee_to': False,
                'computation_blockers': [
                    'missing_historical_total_supply',
                    'missing_fee_growth_trace',
                    'missing_virtual_liquidity_exclusion_basis',
                ],
                'principal_amount0': None,
                'principal_amount1': None,
                'fee_amount0': '0',
                'fee_amount1': '0',
                'protocol_fee_amount0': '0',
                'protocol_fee_amount1': '0',
                'value_warning_codes': [],
                'value_warning_message': None,
            }

        kline_module._db = fake_db
        kline_module._position_metrics_fetcher = fake_fetcher

        try:
            response = await kline_module.on_get_position_metrics(owner='chain:owner-a', status='active')
        finally:
            kline_module._db = original_db
            kline_module._position_metrics_fetcher = original_fetcher

        self.assertEqual(response, {
            'owner': 'chain:owner-a',
            'metrics': [
                {
                    'pool_application': 'chain:pool-app',
                    'pool_id': 7,
                    'token_0': 'QQQ',
                    'token_1': 'TLINERA',
                    'owner': 'chain:owner-a',
                    'status': 'active',
                    'current_liquidity': '0.346087',
                    'position_liquidity_live': '0.346087',
                    'total_supply_live': '1.000000',
                    'exact_share_ratio': '0.346087',
                    'redeemable_amount0': '123.45',
                    'redeemable_amount1': '6.78',
                    'virtual_initial_liquidity': True,
                    'metrics_status': 'partial_live_redeemable_only',
                    'exact_fee_supported': False,
                    'exact_principal_supported': False,
                    'owner_is_fee_to': False,
                    'computation_blockers': [
                        'missing_historical_total_supply',
                        'missing_fee_growth_trace',
                        'missing_virtual_liquidity_exclusion_basis',
                    ],
                    'principal_amount0': None,
                    'principal_amount1': None,
                    'fee_amount0': '0',
                    'fee_amount1': '0',
                    'protocol_fee_amount0': '0',
                    'protocol_fee_amount1': '0',
                    'value_warning_codes': [],
                    'value_warning_message': None,
                },
            ],
        })
        self.assertEqual(fake_db.calls, [{'owner': 'chain:owner-a', 'status': 'active'}])
        self.assertEqual(fake_db.diagnostics[0]['event_type'], 'inexact_position_metrics')
        self.assertEqual(fake_db.diagnostics[0]['owner'], 'chain:owner-a')

    async def test_on_get_position_metrics_returns_400_for_invalid_status(self):
        original_db = kline_module._db
        fake_db = FakeDb(error=ValueError('Invalid positions status'))
        kline_module._db = fake_db

        try:
            response = await kline_module.on_get_position_metrics(owner='chain:owner-a', status='bad')
        finally:
            kline_module._db = original_db

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, b'{"error":"Invalid positions status"}')

    async def test_on_get_diagnostics_exports_persisted_rows(self):
        original_db = kline_module._db
        fake_db = FakeDb()
        fake_db.diagnostics = [
            {
                'diagnostic_id': 1,
                'source': 'ticker',
                'event_type': 'recent_pool_history_mismatch',
                'severity': 'warning',
                'owner': None,
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'status': None,
                'details': {'missing_count': 2},
                'created_at': 123,
            },
        ]
        kline_module._db = fake_db

        try:
            response = await kline_module.on_get_diagnostics(
                source='ticker',
                pool_application='chain:pool-app',
                pool_id=7,
                limit=50,
            )
        finally:
            kline_module._db = original_db

        self.assertEqual(response, {
            'diagnostics': fake_db.diagnostics,
        })

    async def test_on_get_debug_traces_exports_persisted_rows(self):
        original_db = kline_module._db
        fake_db = FakeDb()
        fake_db.debug_traces = [
            {
                'trace_id': 1,
                'source': 'maker',
                'component': 'swap',
                'operation': 'swap',
                'target': 'wallet_application_mutation',
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'request_url': 'http://wallet/query',
                'request_payload': {'query': 'mutation { swap }'},
                'response_status': 200,
                'response_body': {'data': {'swap': True}},
                'error': None,
                'details': {'graphql_errors': None},
                'created_at': 123,
            },
        ]
        kline_module._db = fake_db

        try:
            response = await kline_module.on_get_debug_traces(
                source='maker',
                component='swap',
                pool_application='chain:pool-app',
                pool_id=7,
                limit=50,
            )
        finally:
            kline_module._db = original_db

        self.assertEqual(response, {
            'traces': fake_db.debug_traces,
        })

    async def test_on_get_debug_traces_rejects_non_positive_limit(self):
        original_db = kline_module._db
        kline_module._db = FakeDb()

        try:
            response = await kline_module.on_get_debug_traces(limit=0)
        finally:
            kline_module._db = original_db

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, b'{"error":"limit must be positive"}')

    async def test_on_post_debug_catch_up_run_executes_configured_driver(self):
        class FakeCatchUpDriver:
            def __init__(self):
                self.calls = []

            async def run_once(self, *, max_blocks_per_chain=None):
                self.calls.append(max_blocks_per_chain)
                return {
                    'chain_ids': ['chain-a', 'chain-b'],
                    'total_ingested_count': 3,
                }

        original_driver = kline_module._catch_up_driver
        original_runner = kline_module._catch_up_runner
        fake_driver = FakeCatchUpDriver()
        kline_module._catch_up_driver = fake_driver
        kline_module._catch_up_runner = None

        try:
            response = await kline_module.on_post_debug_catch_up_run(max_blocks=12)
        finally:
            kline_module._catch_up_driver = original_driver
            kline_module._catch_up_runner = original_runner

        self.assertEqual(fake_driver.calls, [12])
        self.assertEqual(response, {
            'trigger': 'admin_repair',
            'scope': 'configured_chains',
            'result': {
                'chain_ids': ['chain-a', 'chain-b'],
                'total_ingested_count': 3,
            },
        })

    async def test_on_post_debug_catch_up_run_can_target_single_chain(self):
        class FakeCatchUpRunner:
            def __init__(self):
                self.calls = []

            async def ingest_until_caught_up(self, chain_id: str, *, max_blocks: int, mode: str = 'catch_up'):
                self.calls.append((chain_id, max_blocks, mode))
                return {
                    'chain_id': chain_id,
                    'ingested_count': 2,
                    'caught_up': True,
                }

        original_driver = kline_module._catch_up_driver
        original_runner = kline_module._catch_up_runner
        original_observability_config = kline_module._observability_config
        fake_runner = FakeCatchUpRunner()
        kline_module._catch_up_driver = None
        kline_module._catch_up_runner = fake_runner
        kline_module._observability_config = {'catch_up_max_blocks_per_chain': 15}

        try:
            response = await kline_module.on_post_debug_catch_up_run(chain_id='chain-a')
        finally:
            kline_module._catch_up_driver = original_driver
            kline_module._catch_up_runner = original_runner
            kline_module._observability_config = original_observability_config

        self.assertEqual(fake_runner.calls, [('chain-a', 15, 'catch_up')])
        self.assertEqual(response, {
            'trigger': 'admin_repair',
            'scope': 'single_chain',
            'result': {
                'chain_id': 'chain-a',
                'ingested_count': 2,
                'caught_up': True,
            },
        })

    async def test_on_post_debug_catch_up_run_rejects_non_positive_max_blocks(self):
        response = await kline_module.on_post_debug_catch_up_run(max_blocks=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, b'{"error":"max_blocks must be positive"}')

    async def test_on_get_debug_pool_bundle_exports_transactions_liquidity_history_and_diagnostics(self):
        original_db = kline_module._db
        fake_db = FakeDb(positions=[
            {
                'transaction_id': 1001,
                'transaction_type': 'AddLiquidity',
                'from_account': 'chain:owner-a',
                'amount_0_in': '10',
                'amount_0_out': '0',
                'amount_1_in': '20',
                'amount_1_out': '0',
                'liquidity': '5',
                'created_at': 100,
            },
        ])
        fake_db.diagnostics = [
            {
                'diagnostic_id': 2,
                'source': 'position_metrics',
                'event_type': 'inexact_position_metrics',
                'severity': 'warning',
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'status': 'active',
                'details': {'metrics_status': 'estimated_live_redeemable_with_history'},
                'created_at': 456,
            },
        ]
        fake_db.gap_summary = {
            'has_internal_gaps': True,
            'start_id': 1000,
            'end_id': 1010,
            'missing_count': 1,
            'missing_ids_sample': [1002],
        }
        kline_module._db = fake_db

        try:
            response = await kline_module.on_get_debug_pool_bundle(
                pool_application='chain:pool-app',
                pool_id=7,
                owner='chain:owner-a',
                transaction_limit=50,
                diagnostics_limit=20,
            )
        finally:
            kline_module._db = original_db

        self.assertEqual(response['pool_application'], 'chain:pool-app')
        self.assertEqual(response['pool_id'], 7)
        self.assertEqual(response['owner'], 'chain:owner-a')
        self.assertEqual(response['transaction_count'], 1)
        self.assertEqual(response['transactions'], fake_db.positions)
        self.assertEqual(response['liquidity_history'], fake_db.positions)
        self.assertEqual(response['gap_summary']['missing_ids_sample'], [1002])
        self.assertEqual(response['diagnostics'], fake_db.diagnostics)
        self.assertIsNone(response['live_recent_audit'])

    async def test_on_get_debug_pool_bundle_can_include_live_recent_window_diff(self):
        original_db = kline_module._db
        original_swap = kline_module._swap
        original_post = kline_module.async_request.post
        fake_db = FakeDb(positions=[
            {
                'transaction_id': 1001,
                'transaction_type': 'AddLiquidity',
                'from_account': 'chain:owner-a',
                'amount_0_in': '10',
                'amount_0_out': '0',
                'amount_1_in': '20',
                'amount_1_out': '0',
                'liquidity': '5',
                'created_at': 100,
            },
        ])
        fake_db.transaction_ids = [1002, 1003, 1005]

        async def fake_post(url, json, timeout):
            self.assertIn('/applications/pool-app', url)
            self.assertEqual(json['query'].strip(), 'query {\n latestTransactions \n}')
            self.assertEqual(timeout, (3, 10))
            return types.SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    'data': {
                        'latestTransactions': [
                            {'transactionId': 1001},
                            {'transactionId': 1002},
                            {'transactionId': 1003},
                            {'transactionId': 1004},
                            {'transactionId': 1005},
                        ],
                    },
                },
            )

        kline_module._db = fake_db
        kline_module._swap = types.SimpleNamespace(base_url='http://swap-host/api/swap')
        kline_module.async_request.post = fake_post

        try:
            response = await kline_module.on_get_debug_pool_bundle(
                pool_application='chain:0xpool-app',
                pool_id=7,
                owner=None,
                transaction_limit=50,
                diagnostics_limit=20,
                include_live_recent=True,
                recent_window=5,
            )
        finally:
            kline_module._db = original_db
            kline_module._swap = original_swap
            kline_module.async_request.post = original_post

        self.assertEqual(response['live_recent_audit'], {
            'pool_id': 7,
            'pool_application': 'chain:0xpool-app',
            'recent_window': 5,
            'window_start_id': 1001,
            'window_end_id': 1005,
            'live_ids': [1001, 1002, 1003, 1004, 1005],
            'db_ids': [1002, 1003, 1005],
            'missing_in_db': [1001, 1004],
            'missing_in_live': [],
        })
        self.assertIn({
            'pool_id': 7,
            'pool_application': 'chain:0xpool-app',
            'start_id': 1001,
            'end_id': 1005,
        }, fake_db.calls)

    async def test_on_get_recent_transaction_audit_returns_db_vs_live_window_diff(self):
        original_db = kline_module._db
        original_swap = kline_module._swap
        original_post = kline_module.async_request.post
        fake_db = FakeDb()
        fake_db.transaction_ids = [1002, 1003, 1005]

        async def fake_post(url, json, timeout):
            self.assertIn('/applications/pool-app', url)
            self.assertEqual(json['query'].strip(), 'query {\n latestTransactions \n}')
            self.assertEqual(timeout, (3, 10))
            return types.SimpleNamespace(
                raise_for_status=lambda: None,
                json=lambda: {
                    'data': {
                        'latestTransactions': [
                            {'transactionId': 1001},
                            {'transactionId': 1002},
                            {'transactionId': 1003},
                            {'transactionId': 1004},
                            {'transactionId': 1005},
                        ],
                    },
                },
            )

        kline_module._db = fake_db
        kline_module._swap = types.SimpleNamespace(base_url='http://swap-host/api/swap')
        kline_module.async_request.post = fake_post

        try:
            response = await kline_module.on_get_recent_transaction_audit(
                pool_id=7,
                pool_application='chain:0xpool-app',
                recent_window=5,
            )
        finally:
            kline_module._db = original_db
            kline_module._swap = original_swap
            kline_module.async_request.post = original_post

        self.assertEqual(response, {
            'pool_id': 7,
            'pool_application': 'chain:0xpool-app',
            'recent_window': 5,
            'window_start_id': 1001,
            'window_end_id': 1005,
            'live_ids': [1001, 1002, 1003, 1004, 1005],
            'db_ids': [1002, 1003, 1005],
            'missing_in_db': [1001, 1004],
            'missing_in_live': [],
        })
        self.assertEqual(fake_db.calls, [{
            'pool_id': 7,
            'pool_application': 'chain:0xpool-app',
            'start_id': 1001,
            'end_id': 1005,
        }])

    async def test_on_get_recent_transaction_audit_returns_400_for_bad_window(self):
        original_db = kline_module._db
        kline_module._db = FakeDb()

        try:
            response = await kline_module.on_get_recent_transaction_audit(
                pool_id=7,
                pool_application='chain:0xpool-app',
                recent_window=0,
            )
        finally:
            kline_module._db = original_db

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, b'{"error":"recent_window must be positive"}')

    async def test_on_get_replay_transaction_audit_returns_first_failure_details(self):
        original_db = kline_module._db
        fake_db = FakeDb(positions=[
            {
                'transaction_id': 1,
                'transaction_type': 'AddLiquidity',
                'from_account': 'chain-a:0xbootstrap-owner',
                'amount_0_in': '100',
                'amount_1_in': '100',
                'amount_0_out': '0',
                'amount_1_out': '0',
                'liquidity': '0',
                'created_at': 1_800_000_000_000,
            },
            {
                'transaction_id': 2,
                'transaction_type': 'BuyToken0',
                'from_account': 'chain-b:0xswapper',
                'amount_0_in': '0',
                'amount_0_out': '9.0',
                'amount_1_in': '10',
                'amount_1_out': '0',
                'liquidity': None,
                'created_at': 1_800_000_001_000,
            },
        ])
        kline_module._db = fake_db

        try:
            response = await kline_module.on_get_replay_transaction_audit(
                pool_id=7,
                pool_application='chain:0xpool-app',
                virtual_initial_liquidity=True,
                start_id=None,
                end_id=None,
                swap_out_tolerance_attos=1,
            )
        finally:
            kline_module._db = original_db

        self.assertEqual(response['pool_id'], 7)
        self.assertEqual(response['pool_application'], 'chain:0xpool-app')
        self.assertTrue(response['virtual_initial_liquidity'])
        self.assertEqual(response['swap_out_tolerance_attos'], 1)
        self.assertFalse(response['audit']['ok'])
        self.assertEqual(
            response['audit']['first_failure']['reason'],
            'pool_history_contains_invalid_swap_amounts',
        )
        self.assertEqual(
            fake_db.calls,
            [{'pool_application': 'chain:0xpool-app', 'pool_id': 7, 'history': True}],
        )

    async def test_on_get_replay_transaction_audit_returns_400_for_negative_tolerance(self):
        original_db = kline_module._db
        kline_module._db = FakeDb()

        try:
            response = await kline_module.on_get_replay_transaction_audit(
                pool_id=7,
                pool_application='chain:0xpool-app',
                virtual_initial_liquidity=False,
                start_id=None,
                end_id=None,
                swap_out_tolerance_attos=-1,
            )
        finally:
            kline_module._db = original_db

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, b'{"error":"swap_out_tolerance_attos must be non-negative"}')

    async def test_on_get_debug_observability_exports_raw_runtime_state(self):
        original_ensure = kline_module._ensure_observability_runtime
        original_container = kline_module._observability_container
        fake_repo = FakeRawRepository()
        fake_repo.cursors = [{'chain_id': 'chain-a', 'sync_status': 'idle'}]
        fake_repo.runs = [{'run_id': 9, 'chain_id': 'chain-a', 'status': 'success'}]
        fake_repo.anomalies = [{'anomaly_id': 3, 'chain_id': 'chain-a', 'status': 'open'}]

        async def fake_ensure():
            return None

        kline_module._ensure_observability_runtime = fake_ensure
        kline_module._observability_container = {'raw_repository': fake_repo}

        try:
            response = await kline_module.on_get_debug_observability(
                chain_ids='chain-a, chain-b',
                run_statuses='success,failed',
                anomaly_statuses='open',
                limit=50,
            )
        finally:
            kline_module._ensure_observability_runtime = original_ensure
            kline_module._observability_container = original_container

        self.assertEqual(response['chain_ids'], ['chain-a', 'chain-b'])
        self.assertEqual(response['run_statuses'], ['success', 'failed'])
        self.assertEqual(response['anomaly_statuses'], ['open'])
        self.assertEqual(response['cursors'], fake_repo.cursors)
        self.assertEqual(response['recent_runs'], fake_repo.runs)
        self.assertEqual(response['anomalies'], fake_repo.anomalies)
        self.assertEqual(
            fake_repo.calls,
            [
                ('list_chain_cursors', ('chain-a', 'chain-b'), 50),
                ('list_recent_ingest_runs', ('chain-a', 'chain-b'), ('success', 'failed'), 50),
                ('list_ingestion_anomalies', ('chain-a', 'chain-b'), ('open',), 50),
            ],
        )

    async def test_on_get_debug_observability_rejects_non_positive_limit(self):
        response = await kline_module.on_get_debug_observability(limit=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, b'{"error":"limit must be positive"}')


if __name__ == '__main__':
    unittest.main()
