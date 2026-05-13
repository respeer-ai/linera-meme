import math


class InventoryController:
    def __init__(
        self,
        *,
        pending_bias_penalty: float,
        long_term_bias_penalty: float,
        anchor_bias_penalty: float,
        long_term_bias_decay: float,
        max_reverse_window_fraction: float,
    ):
        self.pending_bias_penalty = float(pending_bias_penalty)
        self.long_term_bias_penalty = float(long_term_bias_penalty)
        self.anchor_bias_penalty = float(anchor_bias_penalty)
        self.long_term_bias_decay = float(long_term_bias_decay)
        self.max_reverse_window_fraction = float(max_reverse_window_fraction)

        self.pending_buy_quote_notional = {}
        self.pending_sell_quote_notional = {}
        self.long_term_quote_bias = {}
        self.active_minute_plans = {}

    def pending_buy_notional(self, pool_id: int) -> float:
        return self.pending_buy_quote_notional.get(pool_id, 0.0)

    def pending_sell_notional(self, pool_id: int) -> float:
        return self.pending_sell_quote_notional.get(pool_id, 0.0)

    def pending_imbalance(self, pool_id: int) -> float:
        return self.pending_buy_notional(pool_id) - self.pending_sell_notional(pool_id)

    def long_term_bias(self, pool_id: int) -> float:
        return self.long_term_quote_bias.get(pool_id, 0.0)

    def strategy_bias(self, *, pool_id: int, reserve_quote: float, anchor_bias: float) -> float:
        min_quote = max(float(reserve_quote), 1e-12)
        normalized_pending_bias = self.pending_imbalance(pool_id) / min_quote
        normalized_long_term_bias = self.long_term_bias(pool_id) / min_quote
        return (
            self.pending_bias_penalty * normalized_pending_bias
            + self.long_term_bias_penalty * normalized_long_term_bias
            + self.anchor_bias_penalty * anchor_bias
        )

    def queue_buy_quote(self, pool_id: int, quote_notional: float):
        self.pending_buy_quote_notional[pool_id] = self.pending_buy_notional(pool_id) + float(quote_notional)

    def queue_sell_quote(self, pool_id: int, quote_notional: float):
        self.pending_sell_quote_notional[pool_id] = self.pending_sell_notional(pool_id) + float(quote_notional)

    def normalize_quote_for_window(self, pool_id: int, quote_notional: float) -> float:
        quote_notional = float(quote_notional)
        current_net = self.pending_imbalance(pool_id)
        if abs(quote_notional) < 1e-9:
            return 0.0
        if abs(current_net) < 1e-9 or current_net * quote_notional >= 0:
            return quote_notional
        if self.max_reverse_window_fraction <= 0.0:
            return 0.0

        limited_abs = min(
            abs(quote_notional),
            abs(current_net) * self.max_reverse_window_fraction,
        )
        if limited_abs < 1e-6:
            return 0.0
        return math.copysign(limited_abs, quote_notional)

    def flush_plan(self, pool_ids: set[int]) -> list[dict]:
        plan = []
        next_long_term_quote_bias = {}
        for pool_id in pool_ids:
            decayed_bias = self.long_term_bias(pool_id) * self.long_term_bias_decay
            if abs(decayed_bias) >= 1e-9:
                next_long_term_quote_bias[pool_id] = decayed_bias

            quote_notional = self.pending_imbalance(pool_id)
            if abs(quote_notional) < 1e-6:
                continue

            plan.append({
                'pool_id': pool_id,
                'quote_notional': quote_notional,
            })

        self.long_term_quote_bias = next_long_term_quote_bias
        self.pending_buy_quote_notional.clear()
        self.pending_sell_quote_notional.clear()
        return plan

    def set_active_minute_plan(self, pool_id: int, minute_plan):
        if minute_plan is not None and minute_plan.has_remaining_slices():
            self.active_minute_plans[pool_id] = minute_plan
        else:
            self.active_minute_plans.pop(pool_id, None)

    def active_slice_plan(self, pool_id: int) -> list[float]:
        minute_plan = self.active_minute_plans.get(pool_id)
        if minute_plan is None:
            return []
        return minute_plan.remaining_slices()

    def pop_next_slice(self, pool_id: int) -> float | None:
        minute_plan = self.active_minute_plans.get(pool_id)
        if minute_plan is None:
            return None

        next_slice = minute_plan.pop_next_slice()
        if not minute_plan.has_remaining_slices():
            self.active_minute_plans.pop(pool_id, None)
        return next_slice

    def record_executed_quote(self, pool_id: int, executed_quote_notional: float):
        updated_bias = self.long_term_bias(pool_id) + float(executed_quote_notional)
        if abs(updated_bias) >= 1e-9:
            self.long_term_quote_bias[pool_id] = updated_bias
        else:
            self.long_term_quote_bias.pop(pool_id, None)
