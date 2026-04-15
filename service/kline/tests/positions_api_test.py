import sys
import types
import unittest
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

    def get_positions(self, owner: str, status: str):
        self.calls.append({'owner': owner, 'status': status})
        if self.error is not None:
            raise self.error
        return self.positions


class PositionsApiTest(unittest.IsolatedAsyncioTestCase):
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
        self.assertEqual(fake_db.calls, [{'owner': 'chain:owner-a', 'status': 'active'}])

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
                'fee_amount0': None,
                'fee_amount1': None,
                'protocol_fee_amount0': None,
                'protocol_fee_amount1': None,
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
                    'fee_amount0': None,
                    'fee_amount1': None,
                    'protocol_fee_amount0': None,
                    'protocol_fee_amount1': None,
                },
            ],
        })
        self.assertEqual(fake_db.calls, [{'owner': 'chain:owner-a', 'status': 'active'}])

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


if __name__ == '__main__':
    unittest.main()
