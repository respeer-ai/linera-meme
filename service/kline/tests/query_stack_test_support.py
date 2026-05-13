import sys
import types
from pathlib import Path


class QueryStackTestSupport:
    ROOT = Path(__file__).resolve().parents[1]
    SRC_ROOT = ROOT / 'src'
    _installed = False

    class DummyFastAPI:
        def get(self, *_args, **_kwargs):
            return lambda fn: fn

        def post(self, *_args, **_kwargs):
            return lambda fn: fn

        def websocket(self, *_args, **_kwargs):
            return lambda fn: fn

        def on_event(self, *_args, **_kwargs):
            return lambda fn: fn

    class DummyJSONResponse:
        def __init__(self, status_code: int, content: dict):
            self.status_code = status_code
            self.content = content
            self.body = (
                '{'
                + ','.join(f'"{key}":"{value}"' for key, value in content.items())
                + '}'
            ).encode()

    class DummyRequest:
        def __init__(self, query_params=None):
            self.query_params = query_params or {}

    class FakeDb:
        def __init__(self):
            self.calls = []
            self.diagnostics = []

        def get_kline(self, **kwargs):
            self.calls.append(('get_kline', dict(kwargs)))
            return (
                7,
                '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain',
                kwargs['token_0'],
                kwargs['token_1'],
                [{'timestamp': kwargs['start_at'], 'close': '1.23'}],
            )

        def get_kline_information(self, **kwargs):
            self.calls.append(('get_kline_information', dict(kwargs)))
            return {'count': 3, 'timestamp_begin': 300, 'timestamp_end': 100}

        def get_transactions(self, **kwargs):
            self.calls.append(('get_transactions', dict(kwargs)))
            return [{'transaction_id': 11}, {'transaction_id': 12}]

        def get_transactions_information(self, **kwargs):
            self.calls.append(('get_transactions_information', dict(kwargs)))
            return {'count': 2, 'timestamp_begin': 200, 'timestamp_end': 100}

        def get_positions(self, *, owner: str, status: str):
            self.calls.append(('get_positions', {'owner': owner, 'status': status}))
            return [{'pool_id': 7, 'owner': owner, 'status': status}]

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

    class FakeRepository:
        def __init__(self):
            self.calls = []

        def get_candles(self, **kwargs):
            self.calls.append(('get_candles', dict(kwargs)))
            return (9, 'chain:test', 'AAA', 'BBB', [{'close': '3'}])

        def get_candles_information(self, **kwargs):
            self.calls.append(('get_candles_information', dict(kwargs)))
            return {'count': 1}

        def get_transactions(self, **kwargs):
            self.calls.append(('get_transactions', dict(kwargs)))
            return [{'transaction_id': 1}]

        def get_transactions_information(self, **kwargs):
            self.calls.append(('get_transactions_information', dict(kwargs)))
            return {'count': 1}

        def get_positions(self, **kwargs):
            self.calls.append(('get_positions', dict(kwargs)))
            return [{'pool_id': 5}]

    @classmethod
    async def dummy_post(cls, *_args, **_kwargs):
        raise AssertionError('async_request.post should not be used in these tests')

    @classmethod
    def dummy_query(cls, default=None, **_kwargs):
        return default

    @classmethod
    def install(cls):
        if cls._installed:
            return
        if str(cls.SRC_ROOT) not in sys.path:
            sys.path.insert(0, str(cls.SRC_ROOT))

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

        async_request_stub = types.ModuleType('async_request')
        async_request_stub.post = cls.dummy_post
        sys.modules['async_request'] = async_request_stub

        db_stub = types.ModuleType('db')
        db_stub.Db = object
        db_stub.align_timestamp_to_minute_ms = lambda value: value
        sys.modules['db'] = db_stub

        fastapi_stub = types.ModuleType('fastapi')
        fastapi_stub.FastAPI = cls.DummyFastAPI
        fastapi_stub.Query = cls.dummy_query
        fastapi_stub.Request = object
        fastapi_stub.WebSocket = object
        sys.modules['fastapi'] = fastapi_stub

        fastapi_responses_stub = types.ModuleType('fastapi.responses')
        fastapi_responses_stub.JSONResponse = cls.DummyJSONResponse
        sys.modules['fastapi.responses'] = fastapi_responses_stub

        sys.modules['uvicorn'] = types.ModuleType('uvicorn')
        cls._installed = True
