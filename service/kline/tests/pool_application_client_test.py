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


from integration.pool_application_client import PoolApplicationClient  # noqa: E402


class PoolApplicationClientTest(unittest.IsolatedAsyncioTestCase):
    class FakeResponse:
        def __init__(self, payload):
            self.payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self.payload

    async def test_get_position_metrics_payload_falls_back_to_legacy_query(self):
        calls = []

        async def fake_post(*, url, json, timeout):
            calls.append({'url': url, 'json': json, 'timeout': timeout})
            if len(calls) == 1:
                return PoolApplicationClientTest.FakeResponse({
                    'errors': [{'message': 'Unknown field "totalSupply" on type "Pool"'}],
                })
            return PoolApplicationClientTest.FakeResponse({
                'data': {
                    'pool': {'fee_to': None},
                    'virtualInitialLiquidity': False,
                    'liquidity': {'liquidity': '1', 'amount0': '2', 'amount1': '3'},
                    'latestTransactions': [],
                }
            })

        client = PoolApplicationClient(
            base_url='http://swap.example',
            post=fake_post,
            in_k8s=False,
        )

        payload = await client.get_position_metrics_payload(
            pool_application='chain:0xpool-app',
            owner={'chain_id': 'chain-a', 'owner': 'owner-a'},
        )

        self.assertIn('data', payload)
        self.assertEqual(len(calls), 2)
        self.assertIn('totalSupply', calls[0]['json']['query'])
        self.assertNotIn('totalSupply', calls[1]['json']['query'])

    async def test_get_position_metrics_payload_raises_for_non_legacy_graphql_errors(self):
        async def fake_post(*, url, json, timeout):
            return PoolApplicationClientTest.FakeResponse({
                'errors': [{'message': 'boom'}],
            })

        client = PoolApplicationClient(
            base_url='http://swap.example',
            post=fake_post,
            in_k8s=False,
        )

        with self.assertRaises(RuntimeError):
            await client.get_position_metrics_payload(
                pool_application='chain:0xpool-app',
                owner={'chain_id': 'chain-a', 'owner': 'owner-a'},
            )


if __name__ == '__main__':
    unittest.main()
