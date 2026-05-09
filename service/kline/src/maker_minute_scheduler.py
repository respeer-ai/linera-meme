import math
import time

from maker_minute_plan import MinutePlan


class MinuteScheduler:
    def __init__(
        self,
        *,
        execution_window_secs: float,
        min_slices_per_window: int,
        max_slices_per_window: int,
    ):
        self.execution_window_secs = max(float(execution_window_secs), 1.0)
        self.min_slices_per_window = max(int(min_slices_per_window), 1)
        self.max_slices_per_window = max(int(max_slices_per_window), self.min_slices_per_window)
        self.window_started_at = time.monotonic()

    def should_finalize_window(self, now_monotonic: float | None = None) -> bool:
        now_monotonic = time.monotonic() if now_monotonic is None else float(now_monotonic)
        return now_monotonic - self.window_started_at >= self.execution_window_secs

    def build_minute_plan(self, *, quote_notional: float) -> MinutePlan | None:
        quote_notional = float(quote_notional)
        if abs(quote_notional) < 1e-6:
            return None

        magnitude = abs(quote_notional)
        estimated_slices = int(math.ceil(magnitude / max(magnitude * 0.25, 1.0)))
        slice_count = max(self.min_slices_per_window, min(self.max_slices_per_window, estimated_slices))

        sign = 1.0 if quote_notional > 0 else -1.0
        base_slice = magnitude / slice_count
        return MinutePlan(
            quote_notional=quote_notional,
            slice_quotes=[sign * base_slice for _ in range(slice_count)],
        )

    def describe_minute_target(self, *, quote_notional: float) -> dict | None:
        minute_plan = self.build_minute_plan(quote_notional=quote_notional)
        if minute_plan is None:
            return None
        return {
            'target_quote_notional': minute_plan.quote_notional,
            'target_slice_count': minute_plan.target_slice_count,
            'slice_quote_notional': list(minute_plan.slice_quotes),
        }

    def start_new_window(self, now_monotonic: float | None = None):
        self.window_started_at = time.monotonic() if now_monotonic is None else float(now_monotonic)
