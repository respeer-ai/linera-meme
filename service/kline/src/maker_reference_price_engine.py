import math


class ReferencePriceEngine:
    RANGE = 'range'
    TREND = 'trend'

    def __init__(
        self,
        *,
        fair_price_adjustment: float,
        anchor_price_adjustment: float,
        trend_bias_strength: float,
    ):
        self.fair_price_adjustment = float(fair_price_adjustment)
        self.anchor_price_adjustment = float(anchor_price_adjustment)
        self.trend_bias_strength = float(trend_bias_strength)

    def update(self, state, price: float) -> dict:
        min_price = 1e-12
        safe_price = max(float(price), min_price)

        if state.last_price <= 0 or not math.isfinite(state.last_price):
            log_return = 0.0
        else:
            ratio = safe_price / state.last_price
            log_return = math.log(ratio) if ratio > 0 and math.isfinite(ratio) else 0.0

        state.trend_strength *= 0.97
        state.trend_strength += abs(log_return)

        if state.regime == self.RANGE:
            if state.trend_strength > 0.012:
                state.regime = self.TREND
                state.trend_direction = 1 if log_return > 0 else -1
        elif state.regime == self.TREND:
            state.trend_strength *= 0.995
            if state.trend_strength < 0.006:
                state.regime = self.RANGE
                state.trend_direction = 0

        state.last_price = safe_price
        state.reference_price = self._adjust_log_price(
            current_price=safe_price,
            previous_price=state.reference_price,
            adjustment=self.fair_price_adjustment,
        )
        state.anchor_price = self._adjust_log_price(
            current_price=safe_price,
            previous_price=state.anchor_price,
            adjustment=self.anchor_price_adjustment,
        )

        return {
            'price': safe_price,
            'mispricing': self._log_ratio(state.reference_price, safe_price),
            'anchor_bias': self._log_ratio(safe_price, state.anchor_price),
            'regime': state.regime,
            'trend_direction': state.trend_direction,
            'trend_strength': state.trend_strength,
        }

    def directional_scores(
        self,
        *,
        regime: str,
        trend_direction: int,
        mispricing: float,
    ) -> tuple[float, float]:
        if regime == self.RANGE:
            return mispricing, -mispricing

        deviation = abs(mispricing)
        deviation_damp = math.exp(-deviation / 0.02)
        trend_bias = self.trend_bias_strength * trend_direction * deviation_damp
        return mispricing + trend_bias, -mispricing - trend_bias

    def _adjust_log_price(self, *, current_price: float, previous_price: float, adjustment: float) -> float:
        min_price = 1e-12
        if previous_price <= 0 or not math.isfinite(previous_price):
            return max(current_price, min_price)

        ratio = current_price / previous_price
        if ratio <= 0 or not math.isfinite(ratio):
            return max(current_price, min_price)

        delta = math.log(ratio) * adjustment
        return max(previous_price * math.exp(delta), min_price)

    def _log_ratio(self, numerator: float, denominator: float) -> float:
        if numerator <= 0 or denominator <= 0:
            return 0.0
        ratio = numerator / denominator
        if ratio <= 0 or not math.isfinite(ratio):
            return 0.0
        return math.log(ratio)
