import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from maker_minute_plan import MinutePlan  # noqa: E402


class MinutePlanTest(unittest.TestCase):
    def test_pop_next_slice_tracks_progress(self):
        plan = MinutePlan(
            quote_notional=6.0,
            slice_quotes=[2.0, 2.0, 2.0],
        )

        self.assertTrue(plan.has_remaining_slices())
        self.assertEqual(plan.remaining_slices(), [2.0, 2.0, 2.0])
        self.assertEqual(plan.target_slice_count, 3)
        self.assertEqual(plan.remaining_slice_count(), 3)
        self.assertAlmostEqual(plan.remaining_quote_notional(), 6.0)
        self.assertEqual(plan.pop_next_slice(), 2.0)
        self.assertEqual(plan.remaining_slices(), [2.0, 2.0])
        self.assertEqual(plan.remaining_slice_count(), 2)
        self.assertAlmostEqual(plan.executed_quote_notional, 2.0)
        self.assertAlmostEqual(plan.remaining_quote_notional(), 4.0)
        self.assertEqual(plan.pop_next_slice(), 2.0)
        self.assertEqual(plan.pop_next_slice(), 2.0)
        self.assertIsNone(plan.pop_next_slice())
        self.assertFalse(plan.has_remaining_slices())
        self.assertAlmostEqual(plan.executed_quote_notional, 6.0)
        self.assertAlmostEqual(plan.remaining_quote_notional(), 0.0)


if __name__ == '__main__':
    unittest.main()
