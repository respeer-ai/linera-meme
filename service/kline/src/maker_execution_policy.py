import math


class MakerExecutionPolicy:
    def __init__(
        self,
        *,
        max_pending_notional_ratio: float,
        max_trade_ratio: float,
        max_price_impact_ratio: float,
        correction_strength: float,
        mispricing_threshold: float,
        sell_delay_compensation: float,
        activity_notional_ratio: float,
        max_inventory_bias_ratio: float,
    ):
        self.max_pending_notional_ratio = float(max_pending_notional_ratio)
        self.max_trade_ratio = float(max_trade_ratio)
        self.max_price_impact_ratio = float(max_price_impact_ratio)
        self.correction_strength = float(correction_strength)
        self.mispricing_threshold = float(mispricing_threshold)
        self.sell_delay_compensation = float(sell_delay_compensation)
        self.activity_notional_ratio = float(activity_notional_ratio)
        self.max_inventory_bias_ratio = float(max_inventory_bias_ratio)

    def decide_trade(
        self,
        *,
        reserve_0: float,
        reserve_1: float,
        token_0_balance: float,
        token_1_balance: float,
        pending_notional: float,
        effective_mispricing: float,
        directional_signal: float,
    ) -> tuple[float | None, float | None]:
        min_price = 1e-12

        reserve_0 = float(reserve_0)
        reserve_1 = float(reserve_1)
        token_0_balance = float(token_0_balance)
        token_1_balance = float(token_1_balance)
        pending_notional = float(pending_notional)
        effective_mispricing = float(effective_mispricing)
        directional_signal = float(directional_signal)

        if reserve_0 <= 0 or reserve_1 <= 0:
            return (None, None)

        current_price = max(reserve_1 / reserve_0, min_price)
        max_pending_notional = reserve_1 * self.max_pending_notional_ratio
        pending_bias_ratio = pending_notional / max(reserve_1, min_price)

        if abs(effective_mispricing) < self.mispricing_threshold:
            activity_direction = self._activity_direction(
                directional_signal=directional_signal,
                pending_bias_ratio=pending_bias_ratio,
            )
            if activity_direction == 0:
                return (None, None)
            activity_quote = reserve_1 * self.activity_notional_ratio
            return self._quote_trade(
                current_price=current_price,
                reserve_0=reserve_0,
                reserve_1=reserve_1,
                token_0_balance=token_0_balance,
                token_1_balance=token_1_balance,
                quote_notional=activity_quote * activity_direction,
            )

        if effective_mispricing > 0 and pending_notional > max_pending_notional:
            return (None, None)
        if effective_mispricing < 0 and pending_notional < -max_pending_notional:
            return (None, None)

        target_price = self._target_price(
            current_price=current_price,
            effective_mispricing=effective_mispricing,
        )
        constant_product = reserve_0 * reserve_1

        if target_price > current_price:
            amount_1 = self._amount_1_to_target_price(
                reserve_1=reserve_1,
                constant_product=constant_product,
                target_price=target_price,
            )
            amount_1 = min(
                amount_1,
                reserve_1 * self.max_trade_ratio,
                token_1_balance * 0.15,
            )
            if amount_1 < 1e-6:
                return (None, None)
            return (None, amount_1)

        amount_0 = self._amount_0_to_target_price(
            reserve_0=reserve_0,
            constant_product=constant_product,
            target_price=target_price,
        )
        amount_0 = min(
            amount_0 * self.sell_delay_compensation,
            (reserve_1 * self.max_trade_ratio) / current_price,
            token_0_balance * 0.15,
        )
        if amount_0 < 1e-6:
            return (None, None)
        return (amount_0, None)

    def _activity_direction(self, *, directional_signal: float, pending_bias_ratio: float) -> int:
        if abs(pending_bias_ratio) >= self.max_inventory_bias_ratio:
            return -1 if pending_bias_ratio > 0 else 1

        if directional_signal > 0:
            return 1
        if directional_signal < 0:
            return -1
        return 0

    def _quote_trade(
        self,
        *,
        current_price: float,
        reserve_0: float,
        reserve_1: float,
        token_0_balance: float,
        token_1_balance: float,
        quote_notional: float,
    ) -> tuple[float | None, float | None]:
        if quote_notional > 0:
            amount_1 = min(
                quote_notional,
                reserve_1 * self.max_trade_ratio,
                token_1_balance * 0.15,
            )
            if amount_1 < 1e-6:
                return (None, None)
            return (None, amount_1)

        amount_0 = min(
            (abs(quote_notional) / current_price) * self.sell_delay_compensation,
            (reserve_1 * self.max_trade_ratio) / current_price,
            token_0_balance * 0.15,
        )
        if amount_0 < 1e-6:
            return (None, None)
        return (amount_0, None)

    def _target_price(self, *, current_price: float, effective_mispricing: float) -> float:
        max_log_impact = math.log1p(self.max_price_impact_ratio)
        correction_log_move = effective_mispricing * self.correction_strength
        correction_log_move = max(-max_log_impact, min(max_log_impact, correction_log_move))
        return current_price * math.exp(correction_log_move)

    def _amount_1_to_target_price(self, *, reserve_1: float, constant_product: float, target_price: float) -> float:
        required_reserve_1 = math.sqrt(max(target_price, 1e-12) * constant_product)
        return max(0.0, required_reserve_1 - reserve_1)

    def _amount_0_to_target_price(self, *, reserve_0: float, constant_product: float, target_price: float) -> float:
        required_reserve_0 = math.sqrt(constant_product / max(target_price, 1e-12))
        return max(0.0, required_reserve_0 - reserve_0)
