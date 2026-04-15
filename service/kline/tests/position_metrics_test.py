import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


async_request_stub = types.ModuleType('async_request')

async def dummy_post(*_args, **_kwargs):
    raise AssertionError('async_request.post should be stubbed by the test')

async_request_stub.post = dummy_post
sys.modules['async_request'] = async_request_stub

environment_stub = types.ModuleType('environment')
environment_stub.running_in_k8s = lambda: False
sys.modules['environment'] = environment_stub


import position_metrics  # noqa: E402


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


class PositionMetricsTest(unittest.IsolatedAsyncioTestCase):
    def test_pool_application_url_strips_hex_prefix_outside_k8s(self):
        url = position_metrics.pool_application_url(
            'http://swap-host/api/swap',
            'chain-a:0xpool-app',
            in_k8s=False,
        )
        self.assertEqual(
            url,
            'http://swap-host/api/swap/query/chains/chain-a/applications/pool-app',
        )

    def test_build_position_metrics_query_uses_account_object(self):
        query = position_metrics.build_position_metrics_query({
            'chain_id': 'chain-a',
            'owner': '0xowner-a',
        })
        self.assertEqual(query['variables']['owner']['chain_id'], 'chain-a')
        self.assertEqual(query['variables']['owner']['owner'], '0xowner-a')
        self.assertIn('totalSupply', query['query'])
        self.assertIn('virtualInitialLiquidity', query['query'])
        self.assertIn('liquidity(owner: $owner)', query['query'])

    async def test_fetch_live_position_metrics_parses_redeemable_and_swap_blockers(self):
        captured = {}

        async def fake_post(url, json, timeout):
            captured['url'] = url
            captured['json'] = json
            captured['timeout'] = timeout
            return FakeResponse({
                'data': {
                    'totalSupply': '1.500000',
                    'virtualInitialLiquidity': True,
                    'liquidity': {
                        'liquidity': '0.346087',
                        'amount0': '123.45',
                        'amount1': '6.78',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_id': 11,
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '0.346087',
                    'created_at': 1_800_000_000_000,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 10,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xother-owner',
                    'amount_0_in': '1',
                    'amount_1_in': '1',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '1',
                    'created_at': 1_799_999_999_000,
                },
                {
                    'transaction_id': 11,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '0.346087',
                    'amount_1_in': '0.346087',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '0.346087',
                    'created_at': 1_800_000_000_000,
                },
                {
                    'transaction_id': 12,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xthird-owner',
                    'amount_0_in': '0.153913',
                    'amount_1_in': '0.153913',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '0.153913',
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 13,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '0.1',
                    'amount_0_out': '0.093486278677732379',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_002_000,
                },
            ],
            pool_swap_count_since_open=1,
            post=fake_post,
            in_k8s=False,
        )

        self.assertEqual(
            captured['url'],
            'http://swap-host/api/swap/query/chains/chain-b/applications/pool-app',
        )
        self.assertEqual(captured['timeout'], (3, 10))
        self.assertEqual(captured['json']['variables']['owner'], {
            'chain_id': 'chain-a',
            'owner': '0xowner-a',
        })
        self.assertEqual(metrics['redeemable_amount0'], '123.45')
        self.assertEqual(metrics['redeemable_amount1'], '6.78')
        self.assertEqual(metrics['position_liquidity_live'], '0.346087')
        self.assertEqual(metrics['total_supply_live'], '1.500000')
        self.assertTrue(metrics['virtual_initial_liquidity'])
        self.assertFalse(metrics['exact_fee_supported'])
        self.assertFalse(metrics['exact_principal_supported'])
        self.assertEqual(metrics['metrics_status'], 'partial_live_redeemable_only')
        self.assertFalse(metrics['owner_is_fee_to'])
        self.assertIn('pool_has_swap_history_after_position_open', metrics['computation_blockers'])
        self.assertIn('pool_history_bootstrap_supply_unknown', metrics['computation_blockers'])
        self.assertIn('uniswap_v2_fee_split_not_supported_yet', metrics['computation_blockers'])

    async def test_fetch_live_position_metrics_marks_exact_when_no_swaps_and_no_virtual_liquidity(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'totalSupply': '5.0',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '2.0',
                        'amount0': '40',
                        'amount1': '80',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '2.0',
                },
            ],
            pool_swap_count_since_open=0,
            post=fake_post,
            in_k8s=False,
        )

        self.assertEqual(metrics['metrics_status'], 'exact_no_swap_history')
        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertFalse(metrics['owner_is_fee_to'])
        self.assertEqual(metrics['principal_amount0'], '40')
        self.assertEqual(metrics['principal_amount1'], '80')
        self.assertEqual(metrics['fee_amount0'], '0')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0')
        self.assertEqual(metrics['protocol_fee_amount1'], '0')
        self.assertEqual(metrics['computation_blockers'], [])

    async def test_fetch_live_position_metrics_marks_exact_when_no_swaps_with_virtual_liquidity(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'totalSupply': '105.0',
                    'virtualInitialLiquidity': True,
                    'liquidity': {
                        'liquidity': '5.0',
                        'amount0': '40',
                        'amount1': '80',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '5.0',
                },
            ],
            pool_swap_count_since_open=0,
            post=fake_post,
            in_k8s=False,
        )

        self.assertEqual(metrics['metrics_status'], 'exact_no_swap_history')
        self.assertTrue(metrics['virtual_initial_liquidity'])
        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertFalse(metrics['owner_is_fee_to'])
        self.assertEqual(metrics['principal_amount0'], '40')
        self.assertEqual(metrics['principal_amount1'], '80')
        self.assertEqual(metrics['fee_amount0'], '0')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0')
        self.assertEqual(metrics['protocol_fee_amount1'], '0')
        self.assertEqual(metrics['computation_blockers'], [])

    async def test_fetch_live_position_metrics_marks_exact_for_bootstrap_lp_with_swap_history(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'totalSupply': '100.002272933913650825',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '100',
                        'amount0': '90.931824240927035291',
                        'amount1': '109.997499829522206781',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_id': 1,
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '100',
                    'created_at': 1_800_000_000_000,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 1,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '100',
                    'amount_1_in': '100',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '100',
                    'created_at': 1_800_000_000_000,
                },
                {
                    'transaction_id': 2,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '10',
                    'amount_0_out': '9.066108938801491316',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_001_000,
                },
            ],
            pool_swap_count_since_open=1,
            post=fake_post,
            in_k8s=False,
        )

        self.assertEqual(metrics['metrics_status'], 'exact_swap_history_no_post_open_liquidity_changes')
        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertFalse(metrics['owner_is_fee_to'])
        self.assertEqual(metrics['principal_amount0'], '90.907024652497691554')
        self.assertEqual(metrics['principal_amount1'], '109.997499829522206781')
        self.assertEqual(metrics['fee_amount0'], '0.024799588429343737')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0')
        self.assertEqual(metrics['protocol_fee_amount1'], '0')
        self.assertEqual(metrics['computation_blockers'], [])

    async def test_fetch_live_position_metrics_marks_exact_for_partial_lp_without_post_open_liquidity_changes(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'totalSupply': '150.003409400870476237',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '50',
                        'amount0': '45.465912120463517646',
                        'amount1': '54.998749914761103390',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_id': 2,
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '50',
                    'created_at': 1_800_000_001_000,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 1,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xbootstrap-owner',
                    'amount_0_in': '100',
                    'amount_1_in': '100',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '100',
                    'created_at': 1_800_000_000_000,
                },
                {
                    'transaction_id': 2,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '50',
                    'amount_1_in': '50',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '50',
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 3,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '15',
                    'amount_0_out': '13.599163408202236973',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_002_000,
                },
            ],
            pool_swap_count_since_open=1,
            post=fake_post,
            in_k8s=False,
        )

        self.assertEqual(metrics['metrics_status'], 'exact_swap_history_no_post_open_liquidity_changes')
        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertFalse(metrics['owner_is_fee_to'])
        self.assertEqual(metrics['principal_amount0'], '45.453512326248845777')
        self.assertEqual(metrics['principal_amount1'], '54.99874991476110339')
        self.assertEqual(metrics['fee_amount0'], '0.012399794214671869')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0')
        self.assertEqual(metrics['protocol_fee_amount1'], '0')
        self.assertEqual(metrics['computation_blockers'], [])

    async def test_fetch_live_position_metrics_marks_exact_for_fee_to_owner_opening_after_prior_swaps(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'pool': {
                        'fee_to': {
                            'chain_id': 'chain-a',
                            'owner': '0xowner-a',
                        },
                    },
                    'totalSupply': '110.002500227305015907',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '10.002500227305015907',
                        'amount0': '9.095455926391324260',
                        'amount1': '11.002500170477793218',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_id': 3,
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '10.000227293391365082',
                    'created_at': 1_800_000_002_000,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 1,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xbootstrap-owner',
                    'amount_0_in': '100',
                    'amount_1_in': '100',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '100',
                    'created_at': 1_800_000_000_000,
                },
                {
                    'transaction_id': 2,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '10',
                    'amount_0_out': '9.066108938801491316',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 3,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '9.093389106119850868',
                    'amount_1_in': '11',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '10.000227293391365082',
                    'created_at': 1_800_000_002_000,
                },
            ],
            pool_swap_count_since_open=0,
            post=fake_post,
            in_k8s=False,
        )

        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertTrue(metrics['owner_is_fee_to'])
        self.assertEqual(metrics['metrics_status'], 'exact_swap_history_no_post_open_liquidity_changes')
        self.assertEqual(metrics['principal_amount0'], '9.093389106119850867')
        self.assertEqual(metrics['principal_amount1'], '10.999999999999999999')
        self.assertEqual(metrics['fee_amount0'], '0')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0.002066820271473392')
        self.assertEqual(metrics['protocol_fee_amount1'], '0.002500170477793218')
        self.assertEqual(metrics['computation_blockers'], [])

    async def test_fetch_live_position_metrics_marks_exact_for_fee_to_owner_with_virtual_initial_bootstrap(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'pool': {
                        'fee_to': {
                            'chain_id': 'chain-a',
                            'owner': '0xowner-a',
                        },
                    },
                    'totalSupply': '110.002500227305015907',
                    'virtualInitialLiquidity': True,
                    'liquidity': {
                        'liquidity': '10.002500227305015907',
                        'amount0': '9.095455926391324260',
                        'amount1': '11.002500170477793218',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_id': 3,
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '10.000227293391365082',
                    'created_at': 1_800_000_002_000,
                },
            ],
            pool_transaction_history=[
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
                    'amount_1_in': '10',
                    'amount_0_out': '9.066108938801491316',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 3,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '9.093389106119850868',
                    'amount_1_in': '11',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '10.000227293391365082',
                    'created_at': 1_800_000_002_000,
                },
            ],
            pool_swap_count_since_open=0,
            post=fake_post,
            in_k8s=False,
        )

        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertTrue(metrics['owner_is_fee_to'])
        self.assertEqual(metrics['metrics_status'], 'exact_swap_history_no_post_open_liquidity_changes')
        self.assertEqual(metrics['principal_amount0'], '9.093389106119850867')
        self.assertEqual(metrics['principal_amount1'], '10.999999999999999999')
        self.assertEqual(metrics['fee_amount0'], '0')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0.002066820271473392')
        self.assertEqual(metrics['protocol_fee_amount1'], '0.002500170477793218')
        self.assertEqual(metrics['computation_blockers'], [])

    async def test_fetch_live_position_metrics_marks_exact_for_add_then_partial_remove_without_post_change(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'totalSupply': '130.002954814087746072',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '30',
                        'amount0': '27.279547272278110587',
                        'amount1': '32.999249948856662034',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_id': 2,
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '50',
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 3,
                    'transaction_type': 'RemoveLiquidity',
                    'liquidity': '20',
                    'created_at': 1_800_000_002_000,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 1,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xbootstrap-owner',
                    'amount_0_in': '100',
                    'amount_1_in': '100',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '100',
                    'created_at': 1_800_000_000_000,
                },
                {
                    'transaction_id': 2,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '50',
                    'amount_1_in': '50',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '50',
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 3,
                    'transaction_type': 'RemoveLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '0',
                    'amount_1_in': '0',
                    'amount_0_out': '20',
                    'amount_1_out': '20',
                    'liquidity': '20',
                    'created_at': 1_800_000_002_000,
                },
                {
                    'transaction_id': 4,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '13',
                    'amount_0_out': '11.785941620441938710',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_003_000,
                },
            ],
            pool_swap_count_since_open=1,
            post=fake_post,
            in_k8s=False,
        )

        self.assertEqual(metrics['metrics_status'], 'exact_swap_history_no_post_open_liquidity_changes')
        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertFalse(metrics['owner_is_fee_to'])
        self.assertEqual(metrics['principal_amount0'], '27.272107395749307466')
        self.assertEqual(metrics['principal_amount1'], '32.999249948856662034')
        self.assertEqual(metrics['fee_amount0'], '0.007439876528803121')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0')
        self.assertEqual(metrics['protocol_fee_amount1'], '0')
        self.assertEqual(metrics['computation_blockers'], [])

    async def test_fetch_live_position_metrics_marks_exact_for_remove_then_hold_after_swap_history(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'totalSupply': '130.00299103610560718',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '30',
                        'amount0': '27.61341836823568525',
                        'amount1': '32.599349961114979873',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_id': 2,
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '50',
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 4,
                    'transaction_type': 'RemoveLiquidity',
                    'liquidity': '20',
                    'created_at': 1_800_000_003_000,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 1,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xbootstrap-owner',
                    'amount_0_in': '100',
                    'amount_1_in': '100',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '100',
                    'created_at': 1_800_000_000_000,
                },
                {
                    'transaction_id': 2,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '50',
                    'amount_1_in': '50',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '50',
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 3,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '13',
                    'amount_0_out': '11.930155067776952767',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_002_000,
                },
                {
                    'transaction_id': 4,
                    'transaction_type': 'RemoveLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '0',
                    'amount_1_in': '0',
                    'amount_0_out': '18.408945578823790166',
                    'amount_1_out': '21.732899974076653249',
                    'liquidity': '20',
                    'created_at': 1_800_000_003_000,
                },
            ],
            pool_swap_count_since_open=1,
            post=fake_post,
            in_k8s=False,
        )

        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertEqual(metrics['metrics_status'], 'exact_swap_history_no_post_open_liquidity_changes')
        self.assertFalse(metrics['owner_is_fee_to'])
        self.assertEqual(metrics['principal_amount0'], '27.61341836823568525')
        self.assertEqual(metrics['principal_amount1'], '32.599349961114979873')
        self.assertEqual(metrics['fee_amount0'], '0')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0')
        self.assertEqual(metrics['protocol_fee_amount1'], '0')
        self.assertEqual(metrics['computation_blockers'], [])

    async def test_fetch_live_position_metrics_marks_exact_for_remove_then_swap_after_swap_history(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'totalSupply': '130.004525536855024492',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '30',
                        'amount0': '26.313147464528409050',
                        'amount1': '34.214293559470987611',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_id': 2,
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '50',
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 4,
                    'transaction_type': 'RemoveLiquidity',
                    'liquidity': '20',
                    'created_at': 1_800_000_003_000,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 1,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xbootstrap-owner',
                    'amount_0_in': '100',
                    'amount_1_in': '100',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '100',
                    'created_at': 1_800_000_000_000,
                },
                {
                    'transaction_id': 2,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '50',
                    'amount_1_in': '50',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '50',
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 3,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '13',
                    'amount_0_out': '11.930155067776952767',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_002_000,
                },
                {
                    'transaction_id': 4,
                    'transaction_type': 'RemoveLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '0',
                    'amount_1_in': '0',
                    'amount_0_out': '18.408945578823790166',
                    'amount_1_out': '21.732899974076653249',
                    'liquidity': '20',
                    'created_at': 1_800_000_003_000,
                },
                {
                    'transaction_id': 5,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '7',
                    'amount_0_out': '5.633290969822070596',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_004_000,
                },
            ],
            pool_swap_count_since_open=2,
            post=fake_post,
            in_k8s=False,
        )

        self.assertTrue(metrics['exact_fee_supported'])
        self.assertTrue(metrics['exact_principal_supported'])
        self.assertEqual(metrics['metrics_status'], 'exact_swap_history_no_post_open_liquidity_changes')
        self.assertFalse(metrics['owner_is_fee_to'])
        self.assertEqual(metrics['principal_amount0'], '26.309420568294123204')
        self.assertEqual(metrics['principal_amount1'], '34.214293559470987611')
        self.assertEqual(metrics['fee_amount0'], '0.003726896234285846')
        self.assertEqual(metrics['fee_amount1'], '0')
        self.assertEqual(metrics['protocol_fee_amount0'], '0')
        self.assertEqual(metrics['protocol_fee_amount1'], '0')
        self.assertEqual(metrics['computation_blockers'], [])

    async def test_fetch_live_position_metrics_blocks_when_latest_add_happens_after_swap_history(self):
        async def fake_post(url, json, timeout):
            return FakeResponse({
                'data': {
                    'totalSupply': '150.004512399557745466',
                    'virtualInitialLiquidity': False,
                    'liquidity': {
                        'liquidity': '50.001136466956825411',
                        'amount0': '44.133252047115796903',
                        'amount1': '56.666249990808418012',
                    },
                },
            })

        metrics = await position_metrics.fetch_live_position_metrics(
            {
                'owner': 'chain-a:0xowner-a',
                'pool_application': 'chain-b:0xpool-app',
            },
            'http://swap-host/api/swap',
            liquidity_history=[
                {
                    'transaction_id': 3,
                    'transaction_type': 'AddLiquidity',
                    'liquidity': '50.001136466956825411',
                    'created_at': 1_800_000_002_000,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 1,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xbootstrap-owner',
                    'amount_0_in': '100',
                    'amount_1_in': '100',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '100',
                    'created_at': 1_800_000_000_000,
                },
                {
                    'transaction_id': 2,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '10',
                    'amount_0_out': '9.066108938801491315',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_001_000,
                },
                {
                    'transaction_id': 3,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:0xowner-a',
                    'amount_0_in': '45.466945530599254342',
                    'amount_1_in': '55',
                    'amount_0_out': '0',
                    'amount_1_out': '0',
                    'liquidity': '50.001136466956825411',
                    'created_at': 1_800_000_002_000,
                },
                {
                    'transaction_id': 4,
                    'transaction_type': 'BuyToken0',
                    'from_account': 'chain-b:0xswapper',
                    'amount_0_in': '0',
                    'amount_1_in': '5',
                    'amount_0_out': '4.000106894197204745',
                    'amount_1_out': '0',
                    'liquidity': None,
                    'created_at': 1_800_000_003_000,
                },
            ],
            pool_swap_count_since_open=2,
            post=fake_post,
            in_k8s=False,
        )

        self.assertFalse(metrics['exact_fee_supported'])
        self.assertFalse(metrics['exact_principal_supported'])
        self.assertEqual(metrics['metrics_status'], 'partial_live_redeemable_only')
        self.assertIn('pool_has_swap_history_after_position_open', metrics['computation_blockers'])
        self.assertIn(
            'pool_has_swaps_before_latest_position_liquidity_change',
            metrics['computation_blockers'],
        )
        self.assertIn('uniswap_v2_fee_split_not_supported_yet', metrics['computation_blockers'])


if __name__ == '__main__':
    unittest.main()
