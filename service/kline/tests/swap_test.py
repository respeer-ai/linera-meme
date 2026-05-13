import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

if not getattr(sys.modules.get('swap'), '__file__', None):
    sys.modules.pop('swap', None)

async_request_stub = types.ModuleType('async_request')
async_request_stub.post = None
sys.modules.setdefault('async_request', async_request_stub)


from swap import Swap  # noqa: E402


class SwapTest(unittest.TestCase):
    def test_uses_explicit_query_base_url_without_environment_branching(self):
        swap = Swap(
            'swap-host:8080',
            'chain-a',
            'app-a',
            None,
            query_base_url='http://query-service:30080/custom/query/',
        )

        self.assertEqual(
            swap.application_url(),
            'http://query-service:30080/custom/query/chains/chain-a/applications/app-a',
        )

    def test_defaults_to_api_swap_query_base_url(self):
        swap = Swap(
            'swap-host:8080',
            'chain-a',
            'app-a',
            None,
        )

        self.assertEqual(
            swap.application_url(),
            'http://swap-host:8080/api/swap/query/chains/chain-a/applications/app-a',
        )
