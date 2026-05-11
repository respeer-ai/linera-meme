import sys
import types
import unittest
import asyncio
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
        connection = object()

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

    def test_realtime_transaction_history_repository_uses_projection_history_repo(self):
        runtime = KlineRuntime(
            db=self.FakeDb(),
            realtime_db=self.FakeDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )

        repository = runtime.realtime_transaction_history_repository()

        self.assertIsInstance(repository, SettledPoolHistoryProjectionRepository)
        self.assertIsNotNone(repository.settled_trade_projection_repo)
        self.assertIsNotNone(repository.settled_liquidity_projection_repo)

    def test_settled_pool_history_projection_repository_uses_layer3_dependencies(self):
        runtime = KlineRuntime(
            db=self.FakeDb(),
            realtime_db=self.FakeDb(),
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
            realtime_db=self.FakeDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )

        handler = runtime.kline_handler()

        self.assertIsInstance(handler.read_model.repository, SettledTradeProjectionRepository)

    def test_transactions_handler_uses_settled_trade_projection_repository(self):
        runtime = KlineRuntime(
            db=self.FakeDb(),
            realtime_db=self.FakeDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )

        handler = runtime.transactions_handler()

        self.assertIsInstance(handler.read_model.repository, SettledTradeProjectionRepository)

    def test_positions_handler_uses_settled_liquidity_projection_repository(self):
        runtime = KlineRuntime(
            db=self.FakeDb(),
            realtime_db=self.FakeDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )

        handler = runtime.positions_handler()

        self.assertIsInstance(handler.read_model.repository, SettledLiquidityProjectionRepository)

    def test_market_stats_runtime_methods_do_not_call_legacy_db_stats_methods(self):
        class GuardedDb(self.FakeDb):
            def get_ticker(self, **_kwargs):
                raise AssertionError('legacy Db.get_ticker must not be used by runtime stats')

            def get_pool_stats(self, **_kwargs):
                raise AssertionError('legacy Db.get_pool_stats must not be used by runtime stats')

            def get_protocol_stats(self, **_kwargs):
                raise AssertionError('legacy Db.get_protocol_stats must not be used by runtime stats')

        class FakeMarketStatsProjectionRepository:
            def __init__(self):
                self.calls = []

            def get_ticker(self, **kwargs):
                self.calls.append(('get_ticker', dict(kwargs)))
                return [{'token': 'AAA'}]

            def get_pool_stats(self, **kwargs):
                self.calls.append(('get_pool_stats', dict(kwargs)))
                return [{'pool_id': 7}]

        runtime = KlineRuntime(
            db=GuardedDb(),
            realtime_db=GuardedDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )
        repository = FakeMarketStatsProjectionRepository()
        runtime.market_stats_projection_repository = lambda: repository

        self.assertEqual(runtime.get_ticker_stats(interval='1d'), [{'token': 'AAA'}])
        self.assertEqual(runtime.get_pool_stats(interval='1d'), [{'pool_id': 7}])
        self.assertEqual(
            repository.calls,
            [
                ('get_ticker', {'interval': '1d'}),
                ('get_pool_stats', {'interval': '1d'}),
            ],
        )

    def test_protocol_stats_runtime_method_does_not_call_legacy_db_protocol_stats(self):
        class GuardedDb(self.FakeDb):
            def get_protocol_stats(self, **_kwargs):
                raise AssertionError('legacy Db.get_protocol_stats must not be used by runtime protocol stats')

        class FakePoolCatalogRepository:
            def list_current_pools(self):
                return [{'pool_id': 7, 'pool_application': 'chain:pool-app'}]

        class FakeMarketStatsProjectionRepository:
            def get_protocol_stats(self, *, pools):
                self.pools = pools
                return {'pool_count': len(pools)}

        runtime = KlineRuntime(
            db=GuardedDb(),
            realtime_db=GuardedDb(),
            observability_config=None,
            swap=object(),
            websocket_manager=object(),
        )
        market_repo = FakeMarketStatsProjectionRepository()
        runtime.projection_pool_catalog_repository = lambda: FakePoolCatalogRepository()
        runtime.market_stats_projection_repository = lambda: market_repo

        self.assertEqual(asyncio.run(runtime.get_protocol_stats()), {'pool_count': 1})
        self.assertEqual(market_repo.pools, [{'pool_id': 7, 'pool_application': 'chain:pool-app'}])


if __name__ == '__main__':
    unittest.main()
