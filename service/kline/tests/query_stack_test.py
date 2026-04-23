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
    raise AssertionError('async_request.post should not be used in these tests')


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
from query.read_models.candles import CandlesReadModel  # noqa: E402
from query.read_models.positions import PositionsReadModel  # noqa: E402
from query.read_models.transactions import TransactionsReadModel  # noqa: E402
from storage.mysql.projection_repo import ProjectionRepository  # noqa: E402


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
            'chain:pool-app',
            kwargs['token_0'],
            kwargs['token_1'],
            [{'timestamp': kwargs['start_at'], 'close': '1.23'}],
        )

    def get_kline_information(self, **kwargs):
        self.calls.append(('get_kline_information', dict(kwargs)))
        return {
            'count': 3,
            'timestamp_begin': 300,
            'timestamp_end': 100,
        }

    def get_transactions(self, **kwargs):
        self.calls.append(('get_transactions', dict(kwargs)))
        return [{'transaction_id': 11}, {'transaction_id': 12}]

    def get_transactions_information(self, **kwargs):
        self.calls.append(('get_transactions_information', dict(kwargs)))
        return {
            'count': 2,
            'timestamp_begin': 200,
            'timestamp_end': 100,
        }

    def get_positions(self, *, owner: str, status: str):
        self.calls.append(('get_positions', {'owner': owner, 'status': status}))
        return [{'pool_id': 7, 'owner': owner, 'status': status}]

    def record_diagnostic_event(self, **kwargs):
        self.diagnostics.append(dict(kwargs))


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


class ReadModelBridgeTest(unittest.TestCase):
    def test_projection_repository_delegates_to_db(self):
        fake_db = FakeDb()
        repository = ProjectionRepository(fake_db)

        payload = repository.get_candles(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
            interval='1min',
            pool_id=7,
            pool_application='chain:pool-app',
        )

        self.assertEqual(payload[0], 7)
        self.assertEqual(fake_db.calls[0][0], 'get_kline')
        self.assertEqual(fake_db.calls[0][1]['pool_application'], 'chain:pool-app')

    def test_read_models_preserve_phase1_contracts(self):
        repository = FakeRepository()

        candles = CandlesReadModel(repository).get_points(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
            interval='1min',
        )
        transactions = TransactionsReadModel(repository).get_transactions(
            token_0='AAA',
            token_1='BBB',
            start_at=100,
            end_at=200,
        )
        positions = PositionsReadModel(repository).get_positions(
            owner='chain:owner-a',
            status='active',
        )

        self.assertEqual(candles['pool_id'], 9)
        self.assertEqual(candles['points'], [{'close': '3'}])
        self.assertEqual(transactions, [{'transaction_id': 1}])
        self.assertEqual(positions, {
            'owner': 'chain:owner-a',
            'positions': [{'pool_id': 5}],
        })


class QueryStackApiTest(unittest.IsolatedAsyncioTestCase):
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

    async def test_on_get_kline_uses_phase1_handler_stack(self):
        original_db = kline_module._db
        kline_module._db = FakeDb()

        try:
            response = await kline_module.on_get_kline(
                DummyRequest({'request_id': 'req-1'}),
                token0='AAA',
                token1='BBB',
                start_at=100,
                end_at=200,
                interval='1min',
                pool_id=7,
                pool_application='chain:pool-app',
            )
        finally:
            fake_db = kline_module._db
            kline_module._db = original_db

        self.assertEqual(response, {
            'pool_id': 7,
            'pool_application': 'chain:pool-app',
            'token_0': 'AAA',
            'token_1': 'BBB',
            'interval': '1min',
            'start_at': 100,
            'end_at': 200,
            'points': [{'timestamp': 100, 'close': '1.23'}],
        })
        self.assertEqual(fake_db.calls[0][0], 'get_kline')

    async def test_on_get_transactions_and_information_use_phase1_stack(self):
        original_db = kline_module._db
        fake_db = FakeDb()
        kline_module._db = fake_db

        try:
            rows = await kline_module.on_get_transactions(
                token0='AAA',
                token1='BBB',
                start_at=100,
                end_at=200,
            )
            info = await kline_module.on_get_transactions_information(
                token0='AAA',
                token1='BBB',
            )
            combined = await kline_module.on_get_combined_transactions(
                start_at=10,
                end_at=20,
            )
        finally:
            kline_module._db = original_db

        self.assertEqual(rows, [{'transaction_id': 11}, {'transaction_id': 12}])
        self.assertEqual(info, {
            'count': 2,
            'timestamp_begin': 200,
            'timestamp_end': 100,
        })
        self.assertEqual(combined, [{'transaction_id': 11}, {'transaction_id': 12}])
        self.assertEqual(fake_db.calls[0][0], 'get_transactions')
        self.assertIn(
            ('get_transactions_information', {'token_0': 'AAA', 'token_1': 'BBB'}),
            fake_db.calls,
        )
        self.assertIn(
            ('get_transactions', {'token_0': None, 'token_1': None, 'start_at': 10, 'end_at': 20}),
            fake_db.calls,
        )

    async def test_priority1_legacy_rollout_mode_uses_legacy_path_only(self):
        original_db = kline_module._db
        fake_db = FakeDb()
        kline_module._db = fake_db
        os.environ['KLINE_PRIORITY1_ROLLOUT_MODE'] = 'legacy'

        try:
            response = await kline_module.on_get_positions(
                owner='chain:owner-a',
                status='active',
            )
        finally:
            kline_module._db = original_db

        self.assertEqual(response, {
            'owner': 'chain:owner-a',
            'positions': [{'pool_id': 7, 'owner': 'chain:owner-a', 'status': 'active'}],
        })
        self.assertEqual(fake_db.calls, [
            ('get_positions', {'owner': 'chain:owner-a', 'status': 'active'}),
        ])

    async def test_priority1_parity_mismatch_records_diagnostic_event(self):
        class DivergingDb(FakeDb):
            def get_positions(self, *, owner: str, status: str):
                self.calls.append(('get_positions', {'owner': owner, 'status': status}))
                if len(self.calls) == 1:
                    return [{'pool_id': 7, 'owner': owner, 'status': status}]
                return [{'pool_id': 8, 'owner': owner, 'status': status}]

        original_db = kline_module._db
        fake_db = DivergingDb()
        kline_module._db = fake_db
        os.environ['KLINE_PRIORITY1_PARITY'] = '1'

        try:
            with patch('builtins.print'):
                response = await kline_module.on_get_positions(
                    owner='chain:owner-a',
                    status='active',
                )
        finally:
            kline_module._db = original_db

        self.assertEqual(response, {
            'owner': 'chain:owner-a',
            'positions': [{'pool_id': 7, 'owner': 'chain:owner-a', 'status': 'active'}],
        })
        self.assertEqual(len(fake_db.diagnostics), 1)
        self.assertEqual(fake_db.diagnostics[0]['source'], 'phase1_parity')
        self.assertEqual(fake_db.diagnostics[0]['event_type'], 'priority1_mismatch')
