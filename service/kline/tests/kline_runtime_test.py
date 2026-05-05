import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


mysql_stub = types.ModuleType('mysql')
mysql_connector_stub = types.ModuleType('mysql.connector')
mysql_connector_stub.connect = None
mysql_stub.connector = mysql_connector_stub
sys.modules.setdefault('mysql', mysql_stub)
sys.modules.setdefault('mysql.connector', mysql_connector_stub)

pandas_stub = types.ModuleType('pandas')
numpy_stub = types.ModuleType('numpy')
sys.modules.setdefault('pandas', pandas_stub)
sys.modules.setdefault('numpy', numpy_stub)

async_request_stub = types.ModuleType('async_request')
async_request_stub.post = None
sys.modules.setdefault('async_request', async_request_stub)

fastapi_stub = sys.modules.get('fastapi')
if fastapi_stub is None:
    fastapi_stub = types.ModuleType('fastapi')
    sys.modules['fastapi'] = fastapi_stub
if not hasattr(fastapi_stub, 'WebSocket'):
    fastapi_stub.WebSocket = object

swap_stub = types.ModuleType('swap')
swap_stub.Pool = object
swap_stub.Transaction = object
sys.modules.setdefault('swap', swap_stub)


from kline_runtime import KlineRuntime  # noqa: E402
from storage.mysql.settled_liquidity_projection_repo import SettledLiquidityProjectionRepository  # noqa: E402
from storage.mysql.settled_trade_projection_repo import SettledTradeProjectionRepository  # noqa: E402
from storage.mysql.settled_pool_history_projection_repo import SettledPoolHistoryProjectionRepository  # noqa: E402


class KlineRuntimeTest(unittest.TestCase):
    class FakeDb:
        def ensure_fresh_read_connection(self):
            return None

        @property
        def cursor_dict(self):
            raise AssertionError('cursor access is not expected in wiring test')

        @property
        def pools_table(self):
            return 'pools'

        def now_ms(self):
            return 0

    def test_ticker_transaction_history_repository_uses_projection_history_repo(self):
        runtime = KlineRuntime(
            db=self.FakeDb(),
            ticker_db=self.FakeDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )

        repository = runtime.ticker_transaction_history_repository()

        self.assertIsInstance(repository, SettledPoolHistoryProjectionRepository)
        self.assertIsNotNone(repository.settled_trade_projection_repo)
        self.assertIsNotNone(repository.settled_liquidity_projection_repo)

    def test_settled_pool_history_projection_repository_uses_layer3_dependencies(self):
        runtime = KlineRuntime(
            db=self.FakeDb(),
            ticker_db=self.FakeDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )

        repository = runtime.settled_pool_history_projection_repository()

        self.assertIsInstance(repository, SettledPoolHistoryProjectionRepository)
        self.assertIsInstance(repository.settled_trade_projection_repo, SettledTradeProjectionRepository)
        self.assertIsInstance(repository.settled_liquidity_projection_repo, SettledLiquidityProjectionRepository)

    def test_kline_handler_uses_settled_trade_projection_repository(self):
        runtime = KlineRuntime(
            db=self.FakeDb(),
            ticker_db=self.FakeDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )

        handler = runtime.kline_handler()

        self.assertIsInstance(handler.read_model.repository, SettledTradeProjectionRepository)

    def test_transactions_handler_uses_settled_trade_projection_repository(self):
        runtime = KlineRuntime(
            db=self.FakeDb(),
            ticker_db=self.FakeDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )

        handler = runtime.transactions_handler()

        self.assertIsInstance(handler.read_model.repository, SettledTradeProjectionRepository)

    def test_positions_handler_uses_settled_liquidity_projection_repository(self):
        runtime = KlineRuntime(
            db=self.FakeDb(),
            ticker_db=self.FakeDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )

        handler = runtime.positions_handler()

        self.assertIsInstance(handler.read_model.repository, SettledLiquidityProjectionRepository)


if __name__ == '__main__':
    unittest.main()
