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


if __name__ == '__main__':
    unittest.main()
