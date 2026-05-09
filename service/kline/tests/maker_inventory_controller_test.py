import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from maker_inventory_controller import InventoryController  # noqa: E402
from maker_minute_plan import MinutePlan  # noqa: E402


class InventoryControllerTest(unittest.TestCase):
    def make_controller(self):
        return InventoryController(
            pending_bias_penalty=0.9,
            long_term_bias_penalty=1.3,
            anchor_bias_penalty=0.7,
            long_term_bias_decay=0.92,
            max_reverse_window_fraction=0.12,
        )

    def test_queue_updates_pending_imbalance(self):
        controller = self.make_controller()

        controller.queue_buy_quote(7, 5.0)
        controller.queue_sell_quote(7, 2.0)

        self.assertEqual(controller.pending_buy_notional(7), 5.0)
        self.assertEqual(controller.pending_sell_notional(7), 2.0)
        self.assertEqual(controller.pending_imbalance(7), 3.0)

    def test_flush_plan_decays_long_term_bias_and_clears_pending(self):
        controller = self.make_controller()
        controller.long_term_quote_bias[7] = 10.0
        controller.queue_buy_quote(7, 5.0)

        plan = controller.flush_plan({7})

        self.assertEqual(plan, [{'pool_id': 7, 'quote_notional': 5.0}])
        self.assertEqual(controller.pending_buy_notional(7), 0.0)
        self.assertEqual(controller.pending_sell_notional(7), 0.0)
        self.assertAlmostEqual(controller.long_term_bias(7), 9.2)

    def test_record_executed_quote_updates_long_term_bias(self):
        controller = self.make_controller()
        controller.long_term_quote_bias[7] = 2.0

        controller.record_executed_quote(7, -0.5)

        self.assertAlmostEqual(controller.long_term_bias(7), 1.5)

    def test_active_slice_plan_pops_progressively(self):
        controller = self.make_controller()
        controller.set_active_minute_plan(7, MinutePlan(
            quote_notional=6.0,
            slice_quotes=[1.0, 2.0, 3.0],
        ))

        self.assertEqual(controller.active_slice_plan(7), [1.0, 2.0, 3.0])
        self.assertEqual(controller.pop_next_slice(7), 1.0)
        self.assertEqual(controller.pop_next_slice(7), 2.0)
        self.assertEqual(controller.pop_next_slice(7), 3.0)
        self.assertIsNone(controller.pop_next_slice(7))

    def test_normalize_quote_for_window_limits_large_reversal(self):
        controller = self.make_controller()
        controller.queue_buy_quote(7, 10.0)

        normalized = controller.normalize_quote_for_window(7, -8.0)

        self.assertAlmostEqual(normalized, -1.2)

    def test_normalize_quote_for_window_blocks_reversal_when_lock_enabled(self):
        controller = InventoryController(
            pending_bias_penalty=0.9,
            long_term_bias_penalty=1.3,
            anchor_bias_penalty=0.7,
            long_term_bias_decay=0.92,
            max_reverse_window_fraction=0.0,
        )
        controller.queue_buy_quote(7, 10.0)

        normalized = controller.normalize_quote_for_window(7, -8.0)

        self.assertEqual(normalized, 0.0)


if __name__ == '__main__':
    unittest.main()
