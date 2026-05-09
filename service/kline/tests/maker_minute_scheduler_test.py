import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from maker_minute_scheduler import MinuteScheduler  # noqa: E402


class MinuteSchedulerTest(unittest.TestCase):
    def test_build_minute_plan_splits_quote_notional(self):
        scheduler = MinuteScheduler(
            execution_window_secs=15,
            min_slices_per_window=3,
            max_slices_per_window=6,
        )

        minute_plan = scheduler.build_minute_plan(quote_notional=12.0)

        self.assertIsNotNone(minute_plan)
        self.assertEqual(len(minute_plan.slice_quotes), 4)
        self.assertAlmostEqual(sum(minute_plan.slice_quotes), 12.0)
        self.assertTrue(all(slice_quote > 0 for slice_quote in minute_plan.slice_quotes))
        self.assertEqual(minute_plan.target_slice_count, 4)

    def test_build_minute_plan_preserves_sign(self):
        scheduler = MinuteScheduler(
            execution_window_secs=15,
            min_slices_per_window=3,
            max_slices_per_window=6,
        )

        minute_plan = scheduler.build_minute_plan(quote_notional=-9.0)

        self.assertIsNotNone(minute_plan)
        self.assertGreaterEqual(len(minute_plan.slice_quotes), 3)
        self.assertLessEqual(len(minute_plan.slice_quotes), 6)
        self.assertAlmostEqual(sum(minute_plan.slice_quotes), -9.0)
        self.assertTrue(all(slice_quote < 0 for slice_quote in minute_plan.slice_quotes))

    def test_describe_minute_target_exposes_target_fields(self):
        scheduler = MinuteScheduler(
            execution_window_secs=15,
            min_slices_per_window=3,
            max_slices_per_window=6,
        )

        description = scheduler.describe_minute_target(quote_notional=12.0)

        self.assertIsNotNone(description)
        self.assertEqual(description['target_quote_notional'], 12.0)
        self.assertEqual(description['target_slice_count'], 4)
        self.assertAlmostEqual(sum(description['slice_quote_notional']), 12.0)


if __name__ == '__main__':
    unittest.main()
