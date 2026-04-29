import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport


QueryStackTestSupport.install()


import kline as kline_module  # noqa: E402


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
        kline_module._db = QueryStackTestSupport.FakeDb()

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
            fake_db = kline_module._db
            kline_module._db = original_db

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
        self.assertEqual(fake_db.calls[0][0], 'get_kline')

    async def test_on_get_transactions_and_information_use_phase1_stack(self):
        original_db = kline_module._db
        fake_db = QueryStackTestSupport.FakeDb()
        kline_module._db = fake_db

        try:
            rows = await kline_module.on_get_transactions(token0='AAA', token1='BBB', start_at=100, end_at=200)
            info = await kline_module.on_get_transactions_information(token0='AAA', token1='BBB')
            combined = await kline_module.on_get_combined_transactions(start_at=10, end_at=20)
        finally:
            kline_module._db = original_db

        self.assertEqual(rows, [{'transaction_id': 11}, {'transaction_id': 12}])
        self.assertEqual(info, {'count': 2, 'timestamp_begin': 200, 'timestamp_end': 100})
        self.assertEqual(combined, [{'transaction_id': 11}, {'transaction_id': 12}])
        self.assertEqual(fake_db.calls[0][0], 'get_transactions')
        self.assertIn(('get_transactions_information', {'token_0': 'AAA', 'token_1': 'BBB'}), fake_db.calls)
        self.assertIn(('get_transactions', {'token_0': None, 'token_1': None, 'start_at': 10, 'end_at': 20}), fake_db.calls)

    async def test_priority1_legacy_rollout_mode_uses_legacy_path_only(self):
        original_db = kline_module._db
        fake_db = QueryStackTestSupport.FakeDb()
        kline_module._db = fake_db
        os.environ['KLINE_PRIORITY1_ROLLOUT_MODE'] = 'legacy'

        try:
            response = await kline_module.on_get_positions(owner='chain:owner-a', status='active')
        finally:
            kline_module._db = original_db

        self.assertEqual(
            response,
            {'owner': 'chain:owner-a', 'positions': [{'pool_id': 7, 'owner': 'chain:owner-a', 'status': 'active'}]},
        )
        self.assertEqual(fake_db.calls, [('get_positions', {'owner': 'chain:owner-a', 'status': 'active'})])

    async def test_priority1_parity_mismatch_records_diagnostic_event(self):
        class DivergingDb(QueryStackTestSupport.FakeDb):
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
                response = await kline_module.on_get_positions(owner='chain:owner-a', status='active')
        finally:
            kline_module._db = original_db

        self.assertEqual(
            response,
            {'owner': 'chain:owner-a', 'positions': [{'pool_id': 7, 'owner': 'chain:owner-a', 'status': 'active'}]},
        )
        self.assertEqual(len(fake_db.diagnostics), 1)
        self.assertEqual(fake_db.diagnostics[0]['source'], 'phase1_parity')
        self.assertEqual(fake_db.diagnostics[0]['event_type'], 'priority1_mismatch')

    async def test_debug_priority1_rollout_exports_mode_and_recent_mismatches(self):
        original_db = kline_module._db
        fake_db = QueryStackTestSupport.FakeDb()
        fake_db.diagnostics = [
            {
                'diagnostic_id': 9,
                'source': 'phase1_parity',
                'event_type': 'priority1_mismatch',
                'severity': 'warning',
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'status': 'active',
                'details': {'endpoint': '/positions'},
                'created_at': 123,
            },
            {
                'diagnostic_id': 8,
                'source': 'other',
                'event_type': 'ignored',
                'severity': 'info',
                'owner': None,
                'pool_application': None,
                'pool_id': None,
                'status': None,
                'details': {},
                'created_at': 122,
            },
        ]
        kline_module._db = fake_db
        os.environ['KLINE_PRIORITY1_PARITY'] = '1'

        try:
            response = await kline_module.on_get_debug_priority1_rollout(limit=10)
        finally:
            kline_module._db = original_db

        self.assertEqual(response['rollout_mode'], 'new')
        self.assertFalse(response['legacy_mode_enabled'])
        self.assertTrue(response['parity_enabled'])
        self.assertEqual(response['recent_mismatch_count'], 1)
        self.assertEqual(response['recent_mismatches'][0]['event_type'], 'priority1_mismatch')
        self.assertEqual(response['operator_actions'][0]['action'], 'rollback_to_legacy_mode')

    async def test_debug_priority1_rollout_rejects_non_positive_limit(self):
        response = await kline_module.on_get_debug_priority1_rollout(limit=0)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, {'error': 'limit must be positive'})
