import math
import os
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from trader import Trader  # noqa: E402


class MakerSimulationTest(unittest.TestCase):
    def setUp(self):
        self.original_env = {
            'MAX_CORRECTION_NOTIONAL_RATIO': os.environ.get('MAX_CORRECTION_NOTIONAL_RATIO'),
            'ACTIVITY_NOTIONAL_RATIO': os.environ.get('ACTIVITY_NOTIONAL_RATIO'),
            'MAX_REVERSE_WINDOW_FRACTION': os.environ.get('MAX_REVERSE_WINDOW_FRACTION'),
            'MIN_SLICES_PER_WINDOW': os.environ.get('MIN_SLICES_PER_WINDOW'),
            'MAX_SLICES_PER_WINDOW': os.environ.get('MAX_SLICES_PER_WINDOW'),
        }
        os.environ['MAX_CORRECTION_NOTIONAL_RATIO'] = '0.0015'
        os.environ['ACTIVITY_NOTIONAL_RATIO'] = '0.00035'
        os.environ['MAX_REVERSE_WINDOW_FRACTION'] = '0.0'
        os.environ['MIN_SLICES_PER_WINDOW'] = '3'
        os.environ['MAX_SLICES_PER_WINDOW'] = '6'

    def tearDown(self):
        for key, value in self.original_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def _make_trader(self) -> Trader:
        trader = Trader(
            swap=None,
            wallet=None,
            meme=None,
            proxy=None,
            db=None,
        )
        trader.market_drift = 0.0
        return trader

    def _price(self, reserve_0: float, reserve_1: float) -> float:
        return reserve_1 / reserve_0

    def _apply_quote_trade(self, reserve_0: float, reserve_1: float, quote_notional: float) -> tuple[float, float]:
        k = reserve_0 * reserve_1
        if quote_notional > 0:
            new_reserve_1 = reserve_1 + quote_notional
            new_reserve_0 = k / new_reserve_1
            return new_reserve_0, new_reserve_1
        new_reserve_0 = reserve_0 + (abs(quote_notional) / self._price(reserve_0, reserve_1))
        new_reserve_1 = k / new_reserve_0
        return new_reserve_0, new_reserve_1

    def test_simulated_1m_windows_stay_below_extreme_gap_and_range(self):
        trader = self._make_trader()
        reserve_0 = 10_243_750.984077295
        reserve_1 = 8_990.199101773072
        token_0_balance = 250_000.0
        token_1_balance = 40.0
        previous_close = self._price(reserve_0, reserve_1)
        windows = []

        for _ in range(20):
            pool = type('Pool', (), {
                'pool_id': 1000,
                'reserve_0': str(reserve_0),
                'reserve_1': str(reserve_1),
                'token_0': 'AAA',
                'token_1': None,
                'pool_application': type('PoolApp', (), {'short_owner': 'pool-app'})(),
            })()
            price_before = self._price(reserve_0, reserve_1)
            amount_0, amount_1 = trader.trade_amounts(pool, token_0_balance=token_0_balance, token_1_balance=token_1_balance)
            trader.queue_trade(pool, amount_0, amount_1)
            plan = trader.inventory_controller.flush_plan({pool.pool_id})
            price_points = [price_before]
            for item in plan:
                minute_plan = trader.minute_scheduler.build_minute_plan(quote_notional=item['quote_notional'])
                if minute_plan is None:
                    continue
                for slice_quote in minute_plan.slice_quotes:
                    reserve_0, reserve_1 = self._apply_quote_trade(reserve_0, reserve_1, slice_quote)
                    price_points.append(self._price(reserve_0, reserve_1))
                    trader.inventory_controller.record_executed_quote(pool.pool_id, slice_quote)
            open_price = price_points[0]
            close_price = price_points[-1]
            high_price = max(price_points)
            low_price = min(price_points)
            gap_pct = abs((open_price - previous_close) / previous_close) * 100.0
            range_pct = ((high_price - low_price) / open_price) * 100.0
            windows.append({
                'gap_pct': gap_pct,
                'range_pct': range_pct,
                'point_count': len(price_points),
            })
            previous_close = close_price

        self.assertTrue(windows)
        self.assertLess(max(window['gap_pct'] for window in windows), 1.0)
        self.assertLess(max(window['range_pct'] for window in windows), 2.5)
        self.assertTrue(all(window['point_count'] >= 1 for window in windows))


if __name__ == '__main__':
    unittest.main()
