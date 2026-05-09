import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from maker_pool_market_state import PoolMarketState  # noqa: E402
from maker_reference_price_engine import ReferencePriceEngine  # noqa: E402


class ReferencePriceEngineTest(unittest.TestCase):
    def make_engine(self):
        return ReferencePriceEngine(
            fair_price_adjustment=0.08,
            anchor_price_adjustment=0.01,
            trend_bias_strength=0.002,
        )

    def test_update_initializes_reference_and_anchor_price(self):
        state = PoolMarketState(100.0, 200.0)
        engine = self.make_engine()

        signal = engine.update(state, 2.0)

        self.assertEqual(signal['regime'], 'range')
        self.assertAlmostEqual(state.reference_price, 2.0)
        self.assertAlmostEqual(state.anchor_price, 2.0)
        self.assertAlmostEqual(signal['mispricing'], 0.0)
        self.assertAlmostEqual(signal['anchor_bias'], 0.0)

    def test_directional_scores_follow_mispricing_in_range(self):
        engine = self.make_engine()

        buy_score, sell_score = engine.directional_scores(
            regime='range',
            trend_direction=0,
            mispricing=0.05,
        )

        self.assertAlmostEqual(buy_score, 0.05)
        self.assertAlmostEqual(sell_score, -0.05)

    def test_update_can_enter_trend_regime_after_large_move(self):
        state = PoolMarketState(100.0, 200.0)
        engine = self.make_engine()

        engine.update(state, 2.0)
        signal = engine.update(state, 2.3)

        self.assertEqual(signal['regime'], 'trend')
        self.assertEqual(signal['trend_direction'], 1)
        self.assertGreater(signal['trend_strength'], 0.012)


if __name__ == '__main__':
    unittest.main()
