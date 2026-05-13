import sys
import unittest
from pathlib import Path

TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport


QueryStackTestSupport.install()


import kline as kline_module  # noqa: E402


class QueryStackApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_on_get_kline_uses_phase1_handler_stack(self):
        class FakeHandler:
            def __init__(self):
                self.calls = []

            def get_points(self, **kwargs):
                self.calls.append(dict(kwargs))
                return {
                    'pool_id': 7,
                    'pool_application': 'chain:pool-app',
                    'token_0': kwargs['token_0'],
                    'token_1': kwargs['token_1'],
                    'points': [{'timestamp': kwargs['start_at'], 'close': '1.23'}],
                }

        handler = FakeHandler()
        original_builder = kline_module._build_kline_handler
        kline_module._build_kline_handler = lambda: handler

        try:
            response = await kline_module.on_get_kline(
                QueryStackTestSupport.DummyRequest({'request_id': 'req-1'}),
                token0='AAA',
                token1='BBB',
                start_at=100,
                end_at=200,
                interval='1min',
                pool_id=7,
                pool_application='chain:pool-app',
            )
        finally:
            kline_module._build_kline_handler = original_builder

        self.assertEqual(
            response,
            {
                'pool_id': 7,
                'pool_application': 'chain:pool-app',
                'token_0': 'AAA',
                'token_1': 'BBB',
                'interval': '1min',
                'start_at': 100,
                'end_at': 200,
                'points': [{'timestamp': 100, 'close': '1.23'}],
            },
        )
        self.assertEqual(handler.calls[0]['pool_application'], 'chain:pool-app')

    async def test_on_get_transactions_and_information_use_phase1_stack(self):
        class FakeHandler:
            def __init__(self):
                self.calls = []

            def get_transactions(self, **kwargs):
                self.calls.append(('get_transactions', dict(kwargs)))
                return [{'transaction_id': 11}, {'transaction_id': 12}]

            def get_information(self, **kwargs):
                self.calls.append(('get_information', dict(kwargs)))
                return {'count': 2, 'timestamp_begin': 200, 'timestamp_end': 100}

        handler = FakeHandler()
        original_builder = kline_module._build_transactions_handler
        kline_module._build_transactions_handler = lambda: handler

        try:
            rows = await kline_module.on_get_transactions(token0='AAA', token1='BBB', start_at=100, end_at=200, limit=20)
            info = await kline_module.on_get_transactions_information(token0='AAA', token1='BBB')
            combined = await kline_module.on_get_combined_transactions(start_at=10, end_at=20)
        finally:
            kline_module._build_transactions_handler = original_builder

        self.assertEqual(rows, [{'transaction_id': 11}, {'transaction_id': 12}])
        self.assertEqual(info, {'count': 2, 'timestamp_begin': 200, 'timestamp_end': 100})
        self.assertEqual(combined, [{'transaction_id': 11}, {'transaction_id': 12}])
        self.assertEqual(handler.calls[0][0], 'get_transactions')
        self.assertIn(('get_information', {'token_0': 'AAA', 'token_1': 'BBB'}), handler.calls)
        self.assertIn(('get_transactions', {'token_0': None, 'token_1': None, 'start_at': 10, 'end_at': 20, 'limit': None}), handler.calls)
        self.assertIn(('get_transactions', {'token_0': 'AAA', 'token_1': 'BBB', 'start_at': 100, 'end_at': 200, 'limit': 20}), handler.calls)

    async def test_on_get_kline_information_accepts_frontend_daily_interval(self):
        class FakeHandler:
            def __init__(self):
                self.calls = []

            def get_information(self, **kwargs):
                self.calls.append(dict(kwargs))
                return {'count': 2, 'timestamp_begin': 200, 'timestamp_end': 100}

        handler = FakeHandler()
        original_builder = kline_module._build_kline_handler
        kline_module._build_kline_handler = lambda: handler

        try:
            response = await kline_module.on_get_kline_information(
                token0='AAA',
                token1='BBB',
                interval='1d',
                pool_id=7,
                pool_application='chain:pool-app',
            )
        finally:
            kline_module._build_kline_handler = original_builder

        self.assertEqual(response, {'count': 2, 'timestamp_begin': 200, 'timestamp_end': 100})
        self.assertEqual(
            handler.calls,
            [{
                'token_0': 'AAA',
                'token_1': 'BBB',
                'interval': '1d',
                'pool_id': 7,
                'pool_application': 'chain:pool-app',
            }],
        )

    async def test_on_get_positions_uses_phase1_handler_stack(self):
        class FakeHandler:
            def __init__(self):
                self.calls = []

            def get_positions(self, **kwargs):
                self.calls.append(dict(kwargs))
                return {
                    'owner': kwargs['owner'],
                    'positions': [{'pool_id': 7, 'status': kwargs['status']}],
                }

        handler = FakeHandler()
        original_builder = kline_module._build_positions_handler
        kline_module._build_positions_handler = lambda: handler

        try:
            response = await kline_module.on_get_positions(owner='chain:owner-a', status='active')
        finally:
            kline_module._build_positions_handler = original_builder

        self.assertEqual(
            response,
            {'owner': 'chain:owner-a', 'positions': [{'pool_id': 7, 'status': 'active'}]},
        )
        self.assertEqual(handler.calls, [{'owner': 'chain:owner-a', 'status': 'active'}])
