import sys
import types
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


aiohttp_stub = types.ModuleType('aiohttp')
aiohttp_stub.ClientTimeout = lambda **kwargs: kwargs
aiohttp_stub.ClientSession = object
sys.modules.setdefault('aiohttp', aiohttp_stub)


import async_request  # noqa: E402


class AsyncRequestTest(unittest.TestCase):
    def test_async_response_json_parses_decimal_numbers_without_float_rounding(self):
        response = async_request.AsyncResponse(
            status=200,
            headers={},
            text='{"amount":"1.23","amount0Out":1278.003279702912600,"nested":{"fee":0.000000000000000001}}',
            url='http://example.test',
        )

        payload = response.json()

        self.assertEqual(payload['amount'], '1.23')
        self.assertIsInstance(payload['amount0Out'], Decimal)
        self.assertIsInstance(payload['nested']['fee'], Decimal)
        self.assertEqual(payload['amount0Out'], Decimal('1278.003279702912600'))
        self.assertEqual(payload['nested']['fee'], Decimal('0.000000000000000001'))


if __name__ == '__main__':
    unittest.main()
