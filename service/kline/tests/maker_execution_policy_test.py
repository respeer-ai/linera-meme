import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from maker_execution_policy import MakerExecutionPolicy  # noqa: E402


class MakerExecutionPolicyTest(unittest.TestCase):
    def make_policy(self):
        return MakerExecutionPolicy(
            max_pending_notional_ratio=0.03,
            max_trade_ratio=0.015,
            max_correction_notional_ratio=0.003,
            max_price_impact_ratio=0.04,
            correction_strength=0.55,
            mispricing_threshold=0.0015,
            sell_delay_compensation=1.12,
            activity_notional_ratio=0.0008,
            max_inventory_bias_ratio=0.01,
        )

    def test_positive_mispricing_buys_token_0_with_quote_input(self):
        policy = self.make_policy()

        amount_0, amount_1 = policy.decide_trade(
            reserve_0=100.0,
            reserve_1=200.0,
            token_0_balance=50.0,
            token_1_balance=50.0,
            pending_notional=0.0,
            effective_mispricing=0.02,
            directional_signal=0.04,
        )

        self.assertIsNone(amount_0)
        self.assertIsNotNone(amount_1)
        self.assertGreater(amount_1, 0.0)

    def test_negative_mispricing_sells_token_0_with_base_input(self):
        policy = self.make_policy()

        amount_0, amount_1 = policy.decide_trade(
            reserve_0=100.0,
            reserve_1=200.0,
            token_0_balance=50.0,
            token_1_balance=50.0,
            pending_notional=0.0,
            effective_mispricing=-0.02,
            directional_signal=-0.04,
        )

        self.assertIsNotNone(amount_0)
        self.assertGreater(amount_0, 0.0)
        self.assertIsNone(amount_1)

    def test_correction_flow_respects_quote_cap(self):
        policy = self.make_policy()

        amount_0, amount_1 = policy.decide_trade(
            reserve_0=100.0,
            reserve_1=200.0,
            token_0_balance=1000.0,
            token_1_balance=1000.0,
            pending_notional=0.0,
            effective_mispricing=0.20,
            directional_signal=0.20,
        )

        self.assertIsNone(amount_0)
        self.assertIsNotNone(amount_1)
        self.assertAlmostEqual(amount_1, 0.6)

    def test_small_mispricing_uses_controlled_activity_flow(self):
        policy = self.make_policy()

        amount_0, amount_1 = policy.decide_trade(
            reserve_0=100.0,
            reserve_1=200.0,
            token_0_balance=50.0,
            token_1_balance=50.0,
            pending_notional=0.0,
            effective_mispricing=0.0005,
            directional_signal=0.01,
        )

        self.assertIsNone(amount_0)
        self.assertIsNotNone(amount_1)
        self.assertGreater(amount_1, 0.0)

    def test_activity_flow_rebalances_when_pending_bias_is_too_positive(self):
        policy = self.make_policy()

        amount_0, amount_1 = policy.decide_trade(
            reserve_0=100.0,
            reserve_1=200.0,
            token_0_balance=50.0,
            token_1_balance=50.0,
            pending_notional=4.0,
            effective_mispricing=0.0005,
            directional_signal=0.01,
        )

        self.assertIsNotNone(amount_0)
        self.assertGreater(amount_0, 0.0)
        self.assertIsNone(amount_1)

    def test_activity_flow_uses_available_quote_when_base_inventory_is_empty(self):
        policy = self.make_policy()

        amount_0, amount_1 = policy.decide_trade(
            reserve_0=10499900.0,
            reserve_1=8720.0,
            token_0_balance=0.0,
            token_1_balance=100.0,
            pending_notional=0.0,
            effective_mispricing=0.0,
            directional_signal=-0.0001,
        )

        self.assertIsNone(amount_0)
        self.assertIsNotNone(amount_1)
        self.assertGreater(amount_1, 0.0)


if __name__ == '__main__':
    unittest.main()
