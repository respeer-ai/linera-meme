import sys
import types
import unittest
import os
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


mysql_stub = types.ModuleType('mysql')
mysql_connector_stub = types.ModuleType('mysql.connector')
mysql_connector_stub.connect = lambda **_kwargs: None
mysql_stub.connector = mysql_connector_stub
sys.modules['mysql'] = mysql_stub
sys.modules['mysql.connector'] = mysql_connector_stub


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

    async def test_build_position_metrics_fetcher_uses_projection_repository_bridge(self):
        class FakeSwap:
            base_url = 'http://swap.example'

        original_db = kline_module._db
        original_swap = kline_module._swap
        fake_db = FakeDb(positions=[
            {
                'transaction_id': 10,
                'transaction_type': 'AddLiquidity',
                'created_at': 1000,
            },
            {
                'transaction_id': 11,
                'transaction_type': 'BuyToken0',
                'created_at': 2000,
            },
        ])
        fake_db.gap_summary = {
            'has_internal_gaps': False,
            'start_id': 10,
            'end_id': 11,
            'missing_count': 0,
            'missing_ids_sample': [],
        }
        kline_module._db = fake_db
        kline_module._swap = FakeSwap()
        captured = {}

        async def fake_get_position_metrics_payload(*, pool_application, owner):
            captured['pool_application'] = pool_application
            captured['owner'] = dict(owner)
            return {'data': {'latestTransactions': []}}

        def fake_enrich_position_metrics_from_payload(position, payload, **kwargs):
            captured['position'] = position
            captured['payload'] = payload
            captured.update(kwargs)
            return {'metrics_status': 'ok'}

        try:
            with patch.object(
                kline_module.PoolApplicationClient,
                'get_position_metrics_payload',
                side_effect=fake_get_position_metrics_payload,
            ), patch.object(
                kline_module.position_metrics,
                'enrich_position_metrics_from_payload',
                side_effect=fake_enrich_position_metrics_from_payload,
            ):
                fetcher = kline_module._build_position_metrics_fetcher(
                    kline_module._build_projection_repository()
                )
                response = await fetcher({
                    'owner': 'chain:owner-a',
                    'pool_application': 'chain:pool-app',
                    'pool_id': 7,
                    'opened_at': 1500,
                })
        finally:
            kline_module._db = original_db
            kline_module._swap = original_swap

        self.assertEqual(response['live_metrics'], {'metrics_status': 'ok'})
        self.assertIn('snapshot_shadow', response)
        self.assertEqual(captured['pool_application'], 'chain:pool-app')
        self.assertEqual(captured['owner'], {'chain_id': 'chain', 'owner': 'owner-a'})
        self.assertEqual(captured['payload'], {'data': {'latestTransactions': []}})
        self.assertEqual(
            captured['liquidity_history'],
            [
                {
                    'transaction_id': 10,
                    'transaction_type': 'AddLiquidity',
                    'created_at': 1000,
                },
                {
                    'transaction_id': 11,
                    'transaction_type': 'BuyToken0',
                    'created_at': 2000,
                },
            ],
        )
        self.assertEqual(captured['pool_transaction_history'][0]['transaction_id'], 10)
        self.assertEqual(captured['pool_swap_count_since_open'], 1)
        self.assertEqual(captured['pool_history_gap_summary']['start_id'], 10)

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

    async def test_on_get_position_metrics_readiness_debug_aggregates_samples(self):
        original_fetcher = kline_module._position_metrics_fetcher
        original_db = kline_module._db
        kline_module._db = FakeDb(positions=[
            {
                'pool_application': 'chain:pool-a',
                'pool_id': 1,
                'token_0': 'AAA',
                'token_1': 'BBB',
                'owner': 'chain:owner-a',
                'status': 'active',
                'current_liquidity': '5',
            },
            {
                'pool_application': 'chain:pool-b',
                'pool_id': 2,
                'token_0': 'CCC',
                'token_1': 'DDD',
                'owner': 'chain:owner-a',
                'status': 'active',
                'current_liquidity': '9',
            },
            {
                'pool_application': 'chain:pool-c',
                'pool_id': 3,
                'token_0': 'EEE',
                'token_1': 'FFF',
                'owner': 'chain:owner-a',
                'status': 'active',
                'current_liquidity': '12',
            },
            {
                'pool_application': 'chain:pool-d',
                'pool_id': 4,
                'token_0': 'GGG',
                'token_1': 'HHH',
                'owner': 'chain:owner-a',
                'status': 'active',
                'current_liquidity': '10',
            },
        ])

        async def fake_fetcher(position):
            if position['pool_id'] == 1:
                return {
                    'live_metrics': {
                        'metrics_status': 'exact',
                        'exact_fee_supported': True,
                        'exact_principal_supported': True,
                    },
                    'snapshot_shadow': {
                        'owner': position['owner'],
                        'pool_application': position['pool_application'],
                        'pool_id': position['pool_id'],
                        'status': position['status'],
                        'metrics_status': 'exact',
                        'exact_fee_supported': True,
                        'exact_principal_supported': True,
                        'snapshot_shadow': {
                            'readiness': 'candidate',
                            'exact_case': 'post_basis_swaps',
                            'position_basis_snapshot': {
                                'basis_type': 'add_liquidity',
                                'basis_opens_current_round': True,
                                'has_only_zero_liquidity_before_basis': True,
                                'current_round_liquidity_event_count': 1,
                                'current_round_trade_count_before_basis': 0,
                                'trade_count_between_basis_and_fee_free_basis': 0,
                                'exact_current_principal_case': 'post_basis_swaps_without_liquidity_changes',
                                'materialized_protocol_fee_split_case': 'fee_to_opening_add_from_zero',
                                'fee_to_continuity_case': 'continuous_no_changes_after_basis',
                                'fee_to_continuity_change_count_after_basis': 0,
                                'fee_to_continuity_known_before_basis': True,
                                'fee_to_account_at_basis': 'chain:owner-a',
                                'fee_to_account_latest_known': 'chain:owner-a',
                                'protocol_fee_current_owner_provenance_case': 'no_protocol_fee_mints',
                                'basis_protocol_fee_liquidity_owned_by_current_owner': '0',
                                'post_basis_protocol_fee_liquidity_owned_by_current_owner': '0',
                                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '0',
                                'protocol_fee_liquidity_owned_by_current_owner_current': '0',
                                'protocol_fee_liquidity_owned_by_other_accounts': '0',
                                'protocol_fee_liquidity_owner_unknown': '0',
                                'current_round_started_at': 1000,
                                'current_round_started_transaction_id': 10,
                            },
                            'readiness_reason_codes': [],
                            'mismatch_codes': ['pool_last_trade_time_mismatch'],
                        },
                    },
            }
            if position['pool_id'] == 2:
                return {
                'live_metrics': {
                    'metrics_status': 'partial',
                    'exact_fee_supported': False,
                    'exact_principal_supported': False,
                },
                'snapshot_shadow': {
                    'owner': position['owner'],
                    'pool_application': position['pool_application'],
                    'pool_id': position['pool_id'],
                    'status': position['status'],
                    'metrics_status': 'partial',
                    'exact_fee_supported': False,
                    'exact_principal_supported': False,
                    'snapshot_shadow': {
                        'readiness': 'financial_semantics_pending',
                        'exact_case': None,
                            'position_basis_snapshot': {
                                'basis_type': 'remove_liquidity',
                                'basis_opens_current_round': False,
                                'has_only_zero_liquidity_before_basis': False,
                                'current_round_liquidity_event_count': 3,
                                'current_round_trade_count_before_basis': 2,
                                'trade_count_between_basis_and_fee_free_basis': 1,
                                'exact_current_principal_case': None,
                                'materialized_protocol_fee_split_case': 'fee_to_nonzero_prior_add_basis_unresolved',
                                'fee_to_continuity_case': 'changed_after_basis',
                                'fee_to_continuity_change_count_after_basis': 1,
                                'fee_to_continuity_known_before_basis': True,
                                'fee_to_account_at_basis': 'chain:owner-a',
                                'fee_to_account_latest_known': 'chain:owner-b',
                                'protocol_fee_current_owner_provenance_case': 'owner_and_non_owner_mints',
                                'basis_protocol_fee_liquidity_owned_by_current_owner': '2',
                                'post_basis_protocol_fee_liquidity_owned_by_current_owner': '0',
                                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '0',
                                'protocol_fee_liquidity_owned_by_current_owner_current': '2',
                                'protocol_fee_liquidity_owned_by_other_accounts': '3',
                                'protocol_fee_liquidity_owner_unknown': '0',
                                'current_round_started_at': 900,
                                'current_round_started_transaction_id': 8,
                            },
                        'readiness_reason_codes': [
                            'unresolved_fee_to_nonzero_prior_add__basis_only__changed_after_basis__owner_and_non_owner_mints',
                            'materialized_protocol_fee_split_unresolved',
                            'exact_fee_not_supported',
                            'estimated_values',
                        ],
                            'mismatch_codes': [],
                    },
                },
            }
            if position['pool_id'] == 3:
                return {
                'live_metrics': {
                    'metrics_status': 'exact',
                    'exact_fee_supported': True,
                    'exact_principal_supported': True,
                },
                'snapshot_shadow': {
                    'owner': position['owner'],
                    'pool_application': position['pool_application'],
                    'pool_id': position['pool_id'],
                    'status': position['status'],
                    'metrics_status': 'exact',
                    'exact_fee_supported': True,
                    'exact_principal_supported': True,
                    'snapshot_shadow': {
                        'readiness': 'candidate',
                        'exact_case': 'materialized_current_principal_with_later_liquidity',
                        'position_basis_snapshot': {
                            'basis_type': 'add_liquidity',
                            'basis_opens_current_round': False,
                            'has_only_zero_liquidity_before_basis': False,
                            'current_round_liquidity_event_count': 4,
                            'current_round_trade_count_before_basis': 1,
                            'trade_count_between_basis_and_fee_free_basis': 2,
                            'exact_current_principal_case': 'materialized_current_principal_with_later_adds',
                            'materialized_protocol_fee_split_case': 'fee_to_continuous_nonzero_prior_add_basis',
                            'fee_to_continuity_case': 'continuous_no_changes_after_basis',
                            'fee_to_continuity_change_count_after_basis': 0,
                            'fee_to_continuity_known_before_basis': True,
                            'fee_to_account_at_basis': 'chain:owner-a',
                            'fee_to_account_latest_known': 'chain:owner-a',
                            'protocol_fee_current_owner_provenance_case': 'all_mints_owned_by_current_owner',
                            'basis_protocol_fee_liquidity_owned_by_current_owner': '2',
                            'post_basis_protocol_fee_liquidity_owned_by_current_owner': '0',
                            'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '0',
                            'protocol_fee_liquidity_owned_by_current_owner_current': '2',
                            'protocol_fee_liquidity_owned_by_other_accounts': '0',
                            'protocol_fee_liquidity_owner_unknown': '0',
                            'current_round_started_at': 800,
                            'current_round_started_transaction_id': 6,
                        },
                        'readiness_reason_codes': [],
                        'mismatch_codes': [],
                    },
                },
            }
            return {
                'live_metrics': {
                    'metrics_status': 'exact',
                    'exact_fee_supported': True,
                    'exact_principal_supported': True,
                },
                'snapshot_shadow': {
                    'owner': position['owner'],
                    'pool_application': position['pool_application'],
                    'pool_id': position['pool_id'],
                    'status': position['status'],
                    'metrics_status': 'exact',
                    'exact_fee_supported': True,
                    'exact_principal_supported': True,
                    'snapshot_shadow': {
                        'readiness': 'candidate',
                        'exact_case': 'materialized_current_principal_with_later_liquidity',
                        'position_basis_snapshot': {
                            'basis_type': 'add_liquidity',
                            'basis_opens_current_round': False,
                            'has_only_zero_liquidity_before_basis': False,
                            'current_round_liquidity_event_count': 5,
                            'current_round_trade_count_before_basis': 2,
                            'trade_count_between_basis_and_fee_free_basis': 2,
                            'exact_current_principal_case': 'post_basis_liquidity_changes_with_intervening_swaps',
                            'materialized_protocol_fee_split_case': 'current_owner_protocol_fee_component_proven',
                            'fee_to_continuity_case': 'changed_after_basis',
                            'fee_to_continuity_change_count_after_basis': 2,
                            'fee_to_continuity_known_before_basis': True,
                            'fee_to_account_at_basis': 'chain:owner-a',
                            'fee_to_account_latest_known': 'chain:owner-b',
                            'protocol_fee_current_owner_provenance_case': 'owner_and_non_owner_mints',
                            'basis_protocol_fee_liquidity_owned_by_current_owner': '2',
                            'post_basis_protocol_fee_liquidity_owned_by_current_owner': '0',
                            'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': '0',
                            'protocol_fee_liquidity_owned_by_current_owner_current': '2',
                            'protocol_fee_liquidity_owned_by_other_accounts': '3',
                            'protocol_fee_liquidity_owner_unknown': '0',
                            'current_round_started_at': 700,
                            'current_round_started_transaction_id': 5,
                        },
                        'readiness_reason_codes': [],
                        'mismatch_codes': [],
                    },
                },
            }

        kline_module._position_metrics_fetcher = fake_fetcher

        try:
            response = await kline_module.on_get_position_metrics_readiness_debug(
                owner='chain:owner-a',
                status='active',
                sample_limit=10,
            )
        finally:
            kline_module._position_metrics_fetcher = original_fetcher
            kline_module._db = original_db

        self.assertEqual(response['owner'], 'chain:owner-a')
        self.assertEqual(response['status'], 'active')
        self.assertEqual(response['total_positions'], 4)
        self.assertEqual(
            response['readiness_counts'],
            {
                'candidate': 3,
                'snapshot_missing': 0,
                'structure_mismatch': 0,
                'financial_semantics_pending': 1,
                'shadow_unavailable': 0,
            },
        )
        self.assertEqual(
            response['exact_case_counts'],
            {
                'post_basis_swaps': 1,
                'materialized_current_principal_with_later_liquidity': 2,
            },
        )
        self.assertEqual(
            response['readiness_reason_counts'],
            {
                'unresolved_fee_to_nonzero_prior_add__basis_only__changed_after_basis__owner_and_non_owner_mints': 1,
                'materialized_protocol_fee_split_unresolved': 1,
                'exact_fee_not_supported': 1,
                'estimated_values': 1,
            },
        )
        self.assertEqual(
            response['mismatch_code_counts'],
            {
                'pool_last_trade_time_mismatch': 1,
            },
        )
        self.assertEqual(
            response['basis_profile_counts'],
            {
                'add_liquidity|current_round|zero_bootstrap_only': 1,
                'remove_liquidity|not_current_round|non_zero_or_unknown_prefix': 1,
                'add_liquidity|not_current_round|non_zero_or_unknown_prefix': 2,
            },
        )
        self.assertEqual(
            response['current_round_liquidity_event_count_counts'],
            {
                '1': 1,
                '3': 1,
                '4': 1,
                '5': 1,
            },
        )
        self.assertEqual(
            response['current_round_trade_count_before_basis_counts'],
            {
                '0': 1,
                '1': 1,
                '2': 2,
            },
        )
        self.assertEqual(
            response['trade_count_between_basis_and_fee_free_basis_counts'],
            {
                '0': 1,
                '1': 1,
                '2': 2,
            },
        )
        self.assertEqual(
            response['exact_current_principal_case_counts'],
            {
                'post_basis_swaps_without_liquidity_changes': 1,
                'materialized_current_principal_with_later_adds': 1,
                'post_basis_liquidity_changes_with_intervening_swaps': 1,
            },
        )
        self.assertEqual(
            response['materialized_protocol_fee_split_case_counts'],
            {
                'fee_to_opening_add_from_zero': 1,
                'fee_to_nonzero_prior_add_basis_unresolved': 1,
                'fee_to_continuous_nonzero_prior_add_basis': 1,
                'current_owner_protocol_fee_component_proven': 1,
            },
        )
        self.assertEqual(
            response['protocol_fee_split_semantic_counts'],
            {
                'fee_to_opening_add_from_zero_exact': 1,
                'fee_to_nonzero_prior_add_unresolved': 1,
                'fee_to_continuous_nonzero_prior_add_exact': 1,
                'historical_protocol_fee_component_owned_by_current_owner_exact': 1,
            },
        )
        self.assertEqual(
            response['protocol_fee_split_timing_case_counts'],
            {
                'fee_to_opening_add_from_zero|no_current_owner_protocol_fee': 1,
                'fee_to_nonzero_prior_add_basis_unresolved|basis_only': 1,
                'fee_to_continuous_nonzero_prior_add_basis|basis_only': 1,
                'current_owner_protocol_fee_component_proven|basis_only': 1,
            },
        )
        self.assertEqual(
            response['unresolved_protocol_fee_timing_case_counts'],
            {
                'fee_to_nonzero_prior_add_basis_unresolved|basis_only': 1,
            },
        )
        self.assertEqual(
            response['unresolved_protocol_fee_profile_counts'],
            {
                'basis_only|changed_after_basis|owner_and_non_owner_mints': 1,
            },
        )
        self.assertEqual(
            response['unresolved_protocol_fee_semantic_counts'],
            {
                'current_owner_basis_protocol_fee_known_but_fee_to_changed_and_non_owner_mints_present': 1,
            },
        )
        self.assertEqual(
            response['unresolved_protocol_fee_boundary_status_counts'],
            {
                'unsupported_in_current_snapshot_model': 1,
            },
        )
        self.assertEqual(
            response['unresolved_protocol_fee_explanation_counts'],
            {
                'The current owner basis protocol-fee component is known, but fee_to changed after basis and protocol-fee mints for non-owner accounts are also present, so the snapshot cannot prove which later fee dilution belongs to this position.': 1,
            },
        )
        self.assertEqual(
            response['fee_to_continuity_case_counts'],
            {
                'continuous_no_changes_after_basis': 2,
                'changed_after_basis': 2,
            },
        )
        self.assertEqual(
            response['protocol_fee_current_owner_provenance_case_counts'],
            {
                'no_protocol_fee_mints': 1,
                'owner_and_non_owner_mints': 2,
                'all_mints_owned_by_current_owner': 1,
            },
        )
        self.assertEqual(
            response['protocol_fee_current_owner_timing_case_counts'],
            {
                'no_current_owner_protocol_fee': 1,
                'basis_only': 3,
            },
        )
        self.assertEqual(
            response['safe_fee_to_restored_counts'],
            {
                'restored': 1,
                'not_restored': 3,
            },
        )
        self.assertEqual(len(response['samples']), 4)
        self.assertEqual(response['samples'][0]['readiness'], 'candidate')
        self.assertEqual(response['samples'][0]['exact_case'], 'post_basis_swaps')
        self.assertEqual(response['samples'][0]['basis_profile'], 'add_liquidity|current_round|zero_bootstrap_only')
        self.assertEqual(response['samples'][0]['basis_type'], 'add_liquidity')
        self.assertTrue(response['samples'][0]['basis_opens_current_round'])
        self.assertTrue(response['samples'][0]['has_only_zero_liquidity_before_basis'])
        self.assertEqual(response['samples'][0]['current_round_liquidity_event_count'], 1)
        self.assertEqual(response['samples'][0]['current_round_trade_count_before_basis'], 0)
        self.assertEqual(response['samples'][0]['trade_count_between_basis_and_fee_free_basis'], 0)
        self.assertEqual(
            response['samples'][0]['exact_current_principal_case'],
            'post_basis_swaps_without_liquidity_changes',
        )
        self.assertEqual(
            response['samples'][0]['materialized_protocol_fee_split_case'],
            'fee_to_opening_add_from_zero',
        )
        self.assertEqual(
            response['samples'][0]['protocol_fee_split_semantic'],
            'fee_to_opening_add_from_zero_exact',
        )
        self.assertEqual(response['samples'][0]['fee_to_continuity_case'], 'continuous_no_changes_after_basis')
        self.assertEqual(response['samples'][0]['fee_to_continuity_change_count_after_basis'], 0)
        self.assertTrue(response['samples'][0]['fee_to_continuity_known_before_basis'])
        self.assertEqual(response['samples'][0]['fee_to_account_at_basis'], 'chain:owner-a')
        self.assertEqual(response['samples'][0]['fee_to_account_latest_known'], 'chain:owner-a')
        self.assertEqual(response['samples'][0]['protocol_fee_current_owner_provenance_case'], 'no_protocol_fee_mints')
        self.assertEqual(response['samples'][0]['protocol_fee_current_owner_timing_case'], 'no_current_owner_protocol_fee')
        self.assertIsNone(response['samples'][0]['unresolved_protocol_fee_profile'])
        self.assertEqual(response['samples'][0]['unresolved_protocol_fee_semantic'], 'not_applicable_or_unknown')
        self.assertEqual(response['samples'][0]['unresolved_protocol_fee_boundary_status'], 'not_applicable_or_unknown')
        self.assertIsNone(response['samples'][0]['unresolved_protocol_fee_explanation'])
        self.assertEqual(response['samples'][0]['basis_protocol_fee_liquidity_owned_by_current_owner'], '0')
        self.assertEqual(response['samples'][0]['post_basis_protocol_fee_liquidity_owned_by_current_owner'], '0')
        self.assertEqual(
            response['samples'][0]['post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add'],
            '0',
        )
        self.assertEqual(response['samples'][0]['protocol_fee_liquidity_owned_by_current_owner_current'], '0')
        self.assertEqual(response['samples'][0]['protocol_fee_liquidity_owned_by_other_accounts'], '0')
        self.assertEqual(response['samples'][0]['protocol_fee_liquidity_owner_unknown'], '0')
        self.assertFalse(response['samples'][0]['safe_fee_to_restored'])
        self.assertEqual(response['samples'][0]['current_round_started_at'], 1000)
        self.assertEqual(response['samples'][0]['current_round_started_transaction_id'], 10)
        self.assertEqual(response['samples'][0]['mismatch_codes'], ['pool_last_trade_time_mismatch'])
        self.assertEqual(response['samples'][1]['readiness'], 'financial_semantics_pending')
        self.assertIsNone(response['samples'][1]['exact_case'])
        self.assertEqual(
            response['samples'][1]['basis_profile'],
            'remove_liquidity|not_current_round|non_zero_or_unknown_prefix',
        )
        self.assertEqual(response['samples'][1]['current_round_liquidity_event_count'], 3)
        self.assertEqual(response['samples'][1]['current_round_trade_count_before_basis'], 2)
        self.assertEqual(response['samples'][1]['trade_count_between_basis_and_fee_free_basis'], 1)
        self.assertIsNone(response['samples'][1]['exact_current_principal_case'])
        self.assertEqual(
            response['samples'][1]['materialized_protocol_fee_split_case'],
            'fee_to_nonzero_prior_add_basis_unresolved',
        )
        self.assertEqual(
            response['samples'][1]['protocol_fee_split_semantic'],
            'fee_to_nonzero_prior_add_unresolved',
        )
        self.assertEqual(response['samples'][1]['fee_to_continuity_case'], 'changed_after_basis')
        self.assertEqual(response['samples'][1]['fee_to_continuity_change_count_after_basis'], 1)
        self.assertTrue(response['samples'][1]['fee_to_continuity_known_before_basis'])
        self.assertEqual(response['samples'][1]['fee_to_account_at_basis'], 'chain:owner-a')
        self.assertEqual(response['samples'][1]['fee_to_account_latest_known'], 'chain:owner-b')
        self.assertEqual(response['samples'][1]['protocol_fee_current_owner_provenance_case'], 'owner_and_non_owner_mints')
        self.assertEqual(response['samples'][1]['protocol_fee_current_owner_timing_case'], 'basis_only')
        self.assertEqual(
            response['samples'][1]['unresolved_protocol_fee_profile'],
            'basis_only|changed_after_basis|owner_and_non_owner_mints',
        )
        self.assertEqual(
            response['samples'][1]['unresolved_protocol_fee_semantic'],
            'current_owner_basis_protocol_fee_known_but_fee_to_changed_and_non_owner_mints_present',
        )
        self.assertEqual(
            response['samples'][1]['unresolved_protocol_fee_boundary_status'],
            'unsupported_in_current_snapshot_model',
        )
        self.assertEqual(
            response['samples'][1]['unresolved_protocol_fee_explanation'],
            'The current owner basis protocol-fee component is known, but fee_to changed after basis and protocol-fee mints for non-owner accounts are also present, so the snapshot cannot prove which later fee dilution belongs to this position.',
        )
        self.assertEqual(response['samples'][1]['basis_protocol_fee_liquidity_owned_by_current_owner'], '2')
        self.assertEqual(response['samples'][1]['post_basis_protocol_fee_liquidity_owned_by_current_owner'], '0')
        self.assertEqual(
            response['samples'][1]['post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add'],
            '0',
        )
        self.assertEqual(response['samples'][1]['protocol_fee_liquidity_owned_by_current_owner_current'], '2')
        self.assertEqual(response['samples'][1]['protocol_fee_liquidity_owned_by_other_accounts'], '3')
        self.assertEqual(response['samples'][1]['protocol_fee_liquidity_owner_unknown'], '0')
        self.assertFalse(response['samples'][1]['safe_fee_to_restored'])
        self.assertEqual(response['samples'][1]['current_round_started_at'], 900)
        self.assertEqual(response['samples'][1]['current_round_started_transaction_id'], 8)
        self.assertEqual(
            response['samples'][1]['readiness_reason_codes'],
            [
                'unresolved_fee_to_nonzero_prior_add__basis_only__changed_after_basis__owner_and_non_owner_mints',
                'materialized_protocol_fee_split_unresolved',
                'exact_fee_not_supported',
                'estimated_values',
            ],
        )
        self.assertEqual(response['samples'][2]['readiness'], 'candidate')
        self.assertEqual(
            response['samples'][2]['exact_case'],
            'materialized_current_principal_with_later_liquidity',
        )
        self.assertEqual(
            response['samples'][2]['basis_profile'],
            'add_liquidity|not_current_round|non_zero_or_unknown_prefix',
        )
        self.assertEqual(response['samples'][2]['current_round_liquidity_event_count'], 4)
        self.assertEqual(response['samples'][2]['current_round_trade_count_before_basis'], 1)
        self.assertEqual(response['samples'][2]['trade_count_between_basis_and_fee_free_basis'], 2)
        self.assertEqual(
            response['samples'][2]['exact_current_principal_case'],
            'materialized_current_principal_with_later_adds',
        )
        self.assertEqual(
            response['samples'][2]['materialized_protocol_fee_split_case'],
            'fee_to_continuous_nonzero_prior_add_basis',
        )
        self.assertEqual(
            response['samples'][2]['protocol_fee_split_semantic'],
            'fee_to_continuous_nonzero_prior_add_exact',
        )
        self.assertEqual(response['samples'][2]['fee_to_continuity_case'], 'continuous_no_changes_after_basis')
        self.assertEqual(response['samples'][2]['fee_to_continuity_change_count_after_basis'], 0)
        self.assertTrue(response['samples'][2]['fee_to_continuity_known_before_basis'])
        self.assertEqual(response['samples'][2]['fee_to_account_at_basis'], 'chain:owner-a')
        self.assertEqual(response['samples'][2]['fee_to_account_latest_known'], 'chain:owner-a')
        self.assertEqual(
            response['samples'][2]['protocol_fee_current_owner_provenance_case'],
            'all_mints_owned_by_current_owner',
        )
        self.assertEqual(response['samples'][2]['protocol_fee_current_owner_timing_case'], 'basis_only')
        self.assertIsNone(response['samples'][2]['unresolved_protocol_fee_profile'])
        self.assertEqual(response['samples'][2]['unresolved_protocol_fee_semantic'], 'not_applicable_or_unknown')
        self.assertEqual(response['samples'][2]['unresolved_protocol_fee_boundary_status'], 'not_applicable_or_unknown')
        self.assertIsNone(response['samples'][2]['unresolved_protocol_fee_explanation'])
        self.assertEqual(response['samples'][2]['basis_protocol_fee_liquidity_owned_by_current_owner'], '2')
        self.assertEqual(response['samples'][2]['post_basis_protocol_fee_liquidity_owned_by_current_owner'], '0')
        self.assertEqual(
            response['samples'][2]['post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add'],
            '0',
        )
        self.assertEqual(response['samples'][2]['protocol_fee_liquidity_owned_by_current_owner_current'], '2')
        self.assertEqual(response['samples'][2]['protocol_fee_liquidity_owned_by_other_accounts'], '0')
        self.assertEqual(response['samples'][2]['protocol_fee_liquidity_owner_unknown'], '0')
        self.assertTrue(response['samples'][2]['safe_fee_to_restored'])
        self.assertEqual(response['samples'][2]['current_round_started_at'], 800)
        self.assertEqual(response['samples'][2]['current_round_started_transaction_id'], 6)
        self.assertEqual(response['samples'][2]['readiness_reason_codes'], [])
        self.assertEqual(response['samples'][3]['readiness'], 'candidate')
        self.assertEqual(
            response['samples'][3]['exact_case'],
            'materialized_current_principal_with_later_liquidity',
        )
        self.assertEqual(
            response['samples'][3]['basis_profile'],
            'add_liquidity|not_current_round|non_zero_or_unknown_prefix',
        )
        self.assertEqual(response['samples'][3]['current_round_liquidity_event_count'], 5)
        self.assertEqual(response['samples'][3]['current_round_trade_count_before_basis'], 2)
        self.assertEqual(response['samples'][3]['trade_count_between_basis_and_fee_free_basis'], 2)
        self.assertEqual(
            response['samples'][3]['exact_current_principal_case'],
            'post_basis_liquidity_changes_with_intervening_swaps',
        )
        self.assertEqual(
            response['samples'][3]['materialized_protocol_fee_split_case'],
            'current_owner_protocol_fee_component_proven',
        )
        self.assertEqual(
            response['samples'][3]['protocol_fee_split_semantic'],
            'historical_protocol_fee_component_owned_by_current_owner_exact',
        )
        self.assertEqual(response['samples'][3]['fee_to_continuity_case'], 'changed_after_basis')
        self.assertEqual(response['samples'][3]['fee_to_continuity_change_count_after_basis'], 2)
        self.assertTrue(response['samples'][3]['fee_to_continuity_known_before_basis'])
        self.assertEqual(response['samples'][3]['fee_to_account_at_basis'], 'chain:owner-a')
        self.assertEqual(response['samples'][3]['fee_to_account_latest_known'], 'chain:owner-b')
        self.assertEqual(
            response['samples'][3]['protocol_fee_current_owner_provenance_case'],
            'owner_and_non_owner_mints',
        )
        self.assertEqual(response['samples'][3]['protocol_fee_current_owner_timing_case'], 'basis_only')
        self.assertIsNone(response['samples'][3]['unresolved_protocol_fee_profile'])
        self.assertEqual(response['samples'][3]['unresolved_protocol_fee_semantic'], 'not_applicable_or_unknown')
        self.assertEqual(response['samples'][3]['unresolved_protocol_fee_boundary_status'], 'not_applicable_or_unknown')
        self.assertIsNone(response['samples'][3]['unresolved_protocol_fee_explanation'])
        self.assertEqual(response['samples'][3]['basis_protocol_fee_liquidity_owned_by_current_owner'], '2')
        self.assertEqual(response['samples'][3]['post_basis_protocol_fee_liquidity_owned_by_current_owner'], '0')
        self.assertEqual(
            response['samples'][3]['post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add'],
            '0',
        )
        self.assertEqual(response['samples'][3]['protocol_fee_liquidity_owned_by_current_owner_current'], '2')
        self.assertEqual(response['samples'][3]['protocol_fee_liquidity_owned_by_other_accounts'], '3')
        self.assertEqual(response['samples'][3]['protocol_fee_liquidity_owner_unknown'], '0')
        self.assertFalse(response['samples'][3]['safe_fee_to_restored'])
        self.assertEqual(response['samples'][3]['current_round_started_at'], 700)
        self.assertEqual(response['samples'][3]['current_round_started_transaction_id'], 5)
        self.assertEqual(response['samples'][3]['readiness_reason_codes'], [])

    async def test_on_get_position_metrics_readiness_debug_validates_sample_limit(self):
        response = await kline_module.on_get_position_metrics_readiness_debug(
            owner='chain:owner-a',
            status='active',
            sample_limit=0,
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, b'{"error":"sample_limit must be positive"}')

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
        class FakeObservabilityFacade:
            def __init__(self):
                self.calls = []

            async def run_catch_up(self, *, chain_id=None, max_blocks=None):
                self.calls.append((chain_id, max_blocks))
                return {
                    'trigger': 'admin_repair',
                    'scope': 'configured_chains',
                    'result': {
                        'chain_ids': ['chain-a', 'chain-b'],
                        'total_ingested_count': 3,
                    },
                }

        original_facade = kline_module._observability_facade
        fake_facade = FakeObservabilityFacade()
        kline_module._observability_facade = fake_facade

        try:
            response = await kline_module.on_post_debug_catch_up_run(max_blocks=12)
        finally:
            kline_module._observability_facade = original_facade

        self.assertEqual(fake_facade.calls, [(None, 12)])
        self.assertEqual(response, {
            'trigger': 'admin_repair',
            'scope': 'configured_chains',
            'result': {
                'chain_ids': ['chain-a', 'chain-b'],
                'total_ingested_count': 3,
            },
        })

    async def test_on_post_debug_catch_up_run_can_target_single_chain(self):
        class FakeObservabilityFacade:
            def __init__(self):
                self.calls = []

            async def run_catch_up(self, *, chain_id=None, max_blocks=None):
                self.calls.append((chain_id, max_blocks))
                return {
                    'trigger': 'admin_repair',
                    'scope': 'single_chain',
                    'result': {
                        'chain_id': chain_id,
                        'ingested_count': 2,
                        'caught_up': True,
                    },
                }

        original_facade = kline_module._observability_facade
        fake_facade = FakeObservabilityFacade()
        kline_module._observability_facade = fake_facade

        try:
            response = await kline_module.on_post_debug_catch_up_run(chain_id='chain-a')
        finally:
            kline_module._observability_facade = original_facade

        self.assertEqual(fake_facade.calls, [('chain-a', None)])
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
        self.assertIsNone(response['position_basis_snapshot'])
        self.assertIsNone(response['pool_state_snapshot'])
        self.assertIsNone(response['live_recent_audit'])

    async def test_on_get_debug_pool_bundle_can_include_snapshot_state(self):
        original_db = kline_module._db
        original_builder = kline_module._build_position_metrics_repository
        fake_db = FakeDb(positions=[])

        class FakePositionMetricsRepository:
            def get_position_basis_snapshot(self, **kwargs):
                self.position_kwargs = dict(kwargs)
                return {'position_state_id': 'pos-1', 'status': 'active'}

            def get_pool_state_snapshot(self, **kwargs):
                self.pool_kwargs = dict(kwargs)
                return {'pool_state_id': 'pool-1', 'last_transaction_id': 99}

        repository = FakePositionMetricsRepository()
        kline_module._db = fake_db
        kline_module._build_position_metrics_repository = lambda: repository

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
            kline_module._build_position_metrics_repository = original_builder

        self.assertEqual(response['position_basis_snapshot'], {'position_state_id': 'pos-1', 'status': 'active'})
        self.assertEqual(response['pool_state_snapshot'], {'pool_state_id': 'pool-1', 'last_transaction_id': 99})
        self.assertEqual(
            repository.position_kwargs,
            {
                'owner': 'chain:owner-a',
                'pool_application_id': 'chain:pool-app',
                'status': 'active',
            },
        )
        self.assertEqual(
            repository.pool_kwargs,
            {'pool_application_id': 'chain:pool-app'},
        )

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
        original_facade = kline_module._observability_facade

        class FakeObservabilityFacade:
            def __init__(self):
                self.calls = []

            def get_debug_observability(self, *, chain_ids, run_statuses, anomaly_statuses, limit):
                self.calls.append((chain_ids, run_statuses, anomaly_statuses, limit))
                return {
                    'status': {
                        'configured': True,
                        'state': 'ready',
                        'ready': True,
                        'last_error': None,
                        'last_transition_at': 123.0,
                        'starting_in_background': False,
                    },
                    'chain_ids': list(chain_ids),
                    'run_statuses': list(run_statuses),
                    'anomaly_statuses': list(anomaly_statuses),
                    'cursors': [{'chain_id': 'chain-a', 'sync_status': 'idle'}],
                    'recent_runs': [{'run_id': 9, 'chain_id': 'chain-a', 'status': 'success'}],
                    'anomalies': [{'anomaly_id': 3, 'chain_id': 'chain-a', 'status': 'open'}],
                }

        fake_facade = FakeObservabilityFacade()
        kline_module._observability_facade = fake_facade

        try:
            response = await kline_module.on_get_debug_observability(
                chain_ids='chain-a, chain-b',
                run_statuses='success,failed',
                anomaly_statuses='open',
                limit=50,
            )
        finally:
            kline_module._observability_facade = original_facade

        self.assertEqual(response['status']['state'], 'ready')
        self.assertEqual(response['chain_ids'], ['chain-a', 'chain-b'])
        self.assertEqual(response['run_statuses'], ['success', 'failed'])
        self.assertEqual(response['anomaly_statuses'], ['open'])
        self.assertEqual(response['cursors'], [{'chain_id': 'chain-a', 'sync_status': 'idle'}])
        self.assertEqual(response['recent_runs'], [{'run_id': 9, 'chain_id': 'chain-a', 'status': 'success'}])
        self.assertEqual(response['anomalies'], [{'anomaly_id': 3, 'chain_id': 'chain-a', 'status': 'open'}])
        self.assertEqual(
            fake_facade.calls,
            [(('chain-a', 'chain-b'), ('success', 'failed'), ('open',), 50)],
        )

    async def test_on_get_debug_observability_rejects_non_positive_limit(self):
        response = await kline_module.on_get_debug_observability(limit=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.body, b'{"error":"limit must be positive"}')

    async def test_on_post_debug_observability_recover_delegates_to_facade(self):
        original_facade = kline_module._observability_facade

        class FakeObservabilityFacade:
            def __init__(self):
                self.calls = 0

            async def recover(self):
                self.calls += 1
                return {
                    'recovered': True,
                    'status': {
                        'configured': True,
                        'state': 'ready',
                        'ready': True,
                        'last_error': None,
                        'last_transition_at': 1.0,
                        'starting_in_background': False,
                        'recovery_allowed': True,
                    },
                }

        fake_facade = FakeObservabilityFacade()
        kline_module._observability_facade = fake_facade

        try:
            response = await kline_module.on_post_debug_observability_recover()
        finally:
            kline_module._observability_facade = original_facade

        self.assertEqual(fake_facade.calls, 1)
        self.assertTrue(response['recovered'])
        self.assertEqual(response['status']['state'], 'ready')

    async def test_on_post_debug_market_derivation_replay_delegates_to_facade(self):
        original_facade = kline_module._observability_facade

        class FakeObservabilityFacade:
            def __init__(self):
                self.calls = []

            async def run_market_derivation_replay(
                self,
                *,
                raw_table,
                batch_limit,
                max_batches,
                reprocess_reason,
            ):
                self.calls.append((raw_table, batch_limit, max_batches, reprocess_reason))
                return {
                    'result': {
                        'raw_table': raw_table,
                        'batch_limit': batch_limit,
                        'max_batches': max_batches,
                        'reprocess_reason': reprocess_reason,
                    }
                }

        fake_facade = FakeObservabilityFacade()
        kline_module._observability_facade = fake_facade

        try:
            response = await kline_module.on_post_debug_market_derivation_replay_run(
                raw_table='raw_posted_messages',
                batch_limit=10,
                max_batches=2,
                reprocess_reason='manual',
            )
        finally:
            kline_module._observability_facade = original_facade

        self.assertEqual(
            fake_facade.calls,
            [('raw_posted_messages', 10, 2, 'manual')],
        )
        self.assertEqual(response['result']['raw_table'], 'raw_posted_messages')

    async def test_on_post_debug_market_derivation_replay_rejects_invalid_raw_table(self):
        response = await kline_module.on_post_debug_market_derivation_replay_run(
            raw_table='raw_operations'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.body,
            b'{"error":"raw_table must be one of raw_posted_messages"}',
        )

    async def test_on_post_debug_observability_recover_returns_disabled_when_unconfigured(self):
        original_facade = kline_module._observability_facade
        kline_module._observability_facade = None

        try:
            response = await kline_module.on_post_debug_observability_recover()
        finally:
            kline_module._observability_facade = original_facade

        self.assertFalse(response['recovered'])
        self.assertEqual(response['status']['state'], 'disabled')
        self.assertFalse(response['status']['recovery_allowed'])


if __name__ == '__main__':
    unittest.main()
