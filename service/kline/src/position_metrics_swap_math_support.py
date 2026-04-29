from decimal import Decimal
import math


class PositionMetricsSwapMathSupport:
    def __init__(
        self,
        *,
        to_attos,
        from_attos,
        swap_fee_numerator: int,
        swap_fee_denominator: int,
        swap_out_tolerance_attos: int,
    ):
        self.to_attos = to_attos
        self.from_attos = from_attos
        self.swap_fee_numerator = swap_fee_numerator
        self.swap_fee_denominator = swap_fee_denominator
        self.swap_out_tolerance_attos = swap_out_tolerance_attos

    def mint_fee_attos(self, total_supply: int, reserve0: int, reserve1: int, k_last: int) -> int:
        if k_last == 0:
            return 0
        root_k = math.isqrt(reserve0 * reserve1)
        if root_k <= k_last:
            return 0
        denominator = root_k * 5 + k_last
        if denominator == 0:
            return 0
        return total_supply * (root_k - k_last) // denominator

    def sqrt_attos_product(self, amount0: int | None, amount1: int | None) -> int | None:
        if amount0 is None or amount1 is None:
            return None
        if amount0 < 0 or amount1 < 0:
            return None
        return math.isqrt(amount0 * amount1)

    def swap_expected_out_attos(
        self,
        tx_type: str,
        reserve0: int,
        reserve1: int,
        amount0_in: int,
        amount1_in: int,
    ) -> int | None:
        if reserve0 <= 0 or reserve1 <= 0:
            return None
        if tx_type == 'BuyToken0':
            if amount1_in <= 0:
                return None
            amount_in_with_fee = amount1_in * self.swap_fee_numerator
            denominator = reserve1 * self.swap_fee_denominator + amount_in_with_fee
            if denominator <= 0:
                return None
            return amount_in_with_fee * reserve0 // denominator
        if tx_type == 'SellToken0':
            if amount0_in <= 0:
                return None
            amount_in_with_fee = amount0_in * self.swap_fee_numerator
            denominator = reserve0 * self.swap_fee_denominator + amount_in_with_fee
            if denominator <= 0:
                return None
            return amount_in_with_fee * reserve1 // denominator
        return None

    def apply_recorded_swap_attos(
        self,
        tx_type: str,
        reserve0: int,
        reserve1: int,
        *,
        amount0_in: int,
        amount0_out: int,
        amount1_in: int,
        amount1_out: int,
    ) -> tuple[int, int]:
        if tx_type == 'BuyToken0':
            return reserve0 - amount0_out, reserve1 + amount1_in
        return reserve0 + amount0_in, reserve1 - amount1_out

    def infer_hidden_swap_before_batch(
        self,
        reserve0: int,
        reserve1: int,
        pool_transaction_history: list[dict],
        index: int,
    ) -> dict | None:
        tx = pool_transaction_history[index]
        next_tx = pool_transaction_history[index + 1] if index + 1 < len(pool_transaction_history) else None
        if next_tx is None:
            return None
        if int(next_tx.get('created_at') or 0) != int(tx.get('created_at') or 0):
            return None
        if next_tx.get('transaction_type') not in {'BuyToken0', 'SellToken0'}:
            return None
        for candidate in (
            self._solve_hidden_buy_before_swap(reserve0, reserve1, tx),
            self._solve_hidden_sell_before_swap(reserve0, reserve1, tx),
        ):
            if candidate is None:
                continue
            current_reserve0, current_reserve1 = self.apply_recorded_swap_attos(
                candidate['transaction_type'],
                reserve0,
                reserve1,
                amount0_in=self.to_attos(candidate.get('amount_0_in')) or 0,
                amount0_out=self.to_attos(candidate.get('amount_0_out')) or 0,
                amount1_in=self.to_attos(candidate.get('amount_1_in')) or 0,
                amount1_out=self.to_attos(candidate.get('amount_1_out')) or 0,
            )
            for replay_tx in (tx, next_tx):
                expected_out = self.swap_expected_out_attos(
                    replay_tx.get('transaction_type'),
                    current_reserve0,
                    current_reserve1,
                    self.to_attos(replay_tx.get('amount_0_in')) or 0,
                    self.to_attos(replay_tx.get('amount_1_in')) or 0,
                )
                recorded_out = (
                    self.to_attos(replay_tx.get('amount_0_out')) or 0
                    if replay_tx.get('transaction_type') == 'BuyToken0'
                    else self.to_attos(replay_tx.get('amount_1_out')) or 0
                )
                if expected_out is None or not self._swap_out_within_tolerance(expected_out, recorded_out):
                    break
                current_reserve0, current_reserve1 = self.apply_recorded_swap_attos(
                    replay_tx.get('transaction_type'),
                    current_reserve0,
                    current_reserve1,
                    amount0_in=self.to_attos(replay_tx.get('amount_0_in')) or 0,
                    amount0_out=self.to_attos(replay_tx.get('amount_0_out')) or 0,
                    amount1_in=self.to_attos(replay_tx.get('amount_1_in')) or 0,
                    amount1_out=self.to_attos(replay_tx.get('amount_1_out')) or 0,
                )
            else:
                return candidate
        return None

    def _solve_hidden_buy_before_swap(
        self,
        reserve0: int,
        reserve1: int,
        tx: dict,
    ) -> dict | None:
        recorded_amount0_out = self.to_attos(tx.get('amount_0_out')) or 0
        recorded_amount1_out = self.to_attos(tx.get('amount_1_out')) or 0
        amount0_in = self.to_attos(tx.get('amount_0_in')) or 0
        amount1_in = self.to_attos(tx.get('amount_1_in')) or 0
        if tx.get('transaction_type') == 'BuyToken0':
            target_out = recorded_amount0_out
        elif tx.get('transaction_type') == 'SellToken0':
            target_out = recorded_amount1_out
        else:
            return None
        if target_out <= 0:
            return None
        reserve0_d = Decimal(reserve0)
        reserve1_d = Decimal(reserve1)
        target_out_d = Decimal(target_out)
        amount0_in_d = Decimal(amount0_in)
        amount1_in_d = Decimal(amount1_in)

        def hidden_buy_out(x: Decimal) -> Decimal:
            amount_in_with_fee = x * self.swap_fee_numerator
            denominator = reserve1_d * self.swap_fee_denominator + amount_in_with_fee
            if denominator <= 0:
                return Decimal('0')
            return amount_in_with_fee * reserve0_d / denominator

        def replay_error(x: Decimal) -> Decimal:
            hidden_amount0_out = hidden_buy_out(x)
            adjusted_reserve0 = reserve0_d - hidden_amount0_out
            adjusted_reserve1 = reserve1_d + x
            if adjusted_reserve0 <= 0 or adjusted_reserve1 <= 0:
                return Decimal('0') - target_out_d
            if tx.get('transaction_type') == 'BuyToken0':
                amount_in_with_fee = amount1_in_d * self.swap_fee_numerator
                denominator = adjusted_reserve1 * self.swap_fee_denominator + amount_in_with_fee
                expected = amount_in_with_fee * adjusted_reserve0 / denominator
            else:
                amount_in_with_fee = amount0_in_d * self.swap_fee_numerator
                denominator = adjusted_reserve0 * self.swap_fee_denominator + amount_in_with_fee
                expected = amount_in_with_fee * adjusted_reserve1 / denominator
            return expected - target_out_d

        low = Decimal('1')
        high = max(Decimal(reserve1), Decimal(amount1_in or amount0_in or 1))
        low_sign = self._decimal_sign(replay_error(low))
        high_sign = self._decimal_sign(replay_error(high))
        while high_sign != 0 and high_sign == low_sign and high < Decimal(reserve1 * 1024):
            high *= 2
            high_sign = self._decimal_sign(replay_error(high))
        if low_sign != 0 and high_sign != 0 and high_sign == low_sign:
            return None
        for _ in range(256):
            mid = (low + high) / 2
            mid_sign = self._decimal_sign(replay_error(mid))
            if mid_sign == 0:
                low = high = mid
                break
            if low_sign == 0 or mid_sign == low_sign:
                low = mid
                low_sign = mid_sign
            else:
                high = mid
                high_sign = mid_sign
        hidden_amount1_in = int(high.to_integral_value())
        if hidden_amount1_in <= 0:
            return None
        hidden_amount0_out = self.swap_expected_out_attos(
            'BuyToken0',
            reserve0,
            reserve1,
            0,
            hidden_amount1_in,
        )
        if hidden_amount0_out is None or hidden_amount0_out <= 0 or hidden_amount0_out >= reserve0:
            return None
        return {
            'transaction_id': None,
            'transaction_type': 'BuyToken0',
            'from_account': None,
            'amount_0_in': None,
            'amount_0_out': self.from_attos(hidden_amount0_out),
            'amount_1_in': self.from_attos(hidden_amount1_in),
            'amount_1_out': None,
            'liquidity': None,
            'created_at': tx.get('created_at'),
            'synthetic_hidden_swap': True,
        }

    def _solve_hidden_sell_before_swap(
        self,
        reserve0: int,
        reserve1: int,
        tx: dict,
    ) -> dict | None:
        recorded_amount0_out = self.to_attos(tx.get('amount_0_out')) or 0
        recorded_amount1_out = self.to_attos(tx.get('amount_1_out')) or 0
        amount0_in = self.to_attos(tx.get('amount_0_in')) or 0
        amount1_in = self.to_attos(tx.get('amount_1_in')) or 0
        if tx.get('transaction_type') == 'BuyToken0':
            target_out = recorded_amount0_out
        elif tx.get('transaction_type') == 'SellToken0':
            target_out = recorded_amount1_out
        else:
            return None
        if target_out <= 0:
            return None
        reserve0_d = Decimal(reserve0)
        reserve1_d = Decimal(reserve1)
        target_out_d = Decimal(target_out)
        amount0_in_d = Decimal(amount0_in)
        amount1_in_d = Decimal(amount1_in)

        def hidden_sell_out(x: Decimal) -> Decimal:
            amount_in_with_fee = x * self.swap_fee_numerator
            denominator = reserve0_d * self.swap_fee_denominator + amount_in_with_fee
            if denominator <= 0:
                return Decimal('0')
            return amount_in_with_fee * reserve1_d / denominator

        def replay_error(x: Decimal) -> Decimal:
            hidden_amount1_out = hidden_sell_out(x)
            adjusted_reserve0 = reserve0_d + x
            adjusted_reserve1 = reserve1_d - hidden_amount1_out
            if adjusted_reserve0 <= 0 or adjusted_reserve1 <= 0:
                return Decimal('0') - target_out_d
            if tx.get('transaction_type') == 'BuyToken0':
                amount_in_with_fee = amount1_in_d * self.swap_fee_numerator
                denominator = adjusted_reserve1 * self.swap_fee_denominator + amount_in_with_fee
                expected = amount_in_with_fee * adjusted_reserve0 / denominator
            else:
                amount_in_with_fee = amount0_in_d * self.swap_fee_numerator
                denominator = adjusted_reserve0 * self.swap_fee_denominator + amount_in_with_fee
                expected = amount_in_with_fee * adjusted_reserve1 / denominator
            return expected - target_out_d

        low = Decimal('1')
        high = max(Decimal(reserve0), Decimal(amount0_in or amount1_in or 1))
        low_sign = self._decimal_sign(replay_error(low))
        high_sign = self._decimal_sign(replay_error(high))
        while high_sign != 0 and high_sign == low_sign and high < Decimal(reserve0 * 1024):
            high *= 2
            high_sign = self._decimal_sign(replay_error(high))
        if low_sign != 0 and high_sign != 0 and high_sign == low_sign:
            return None
        for _ in range(256):
            mid = (low + high) / 2
            mid_sign = self._decimal_sign(replay_error(mid))
            if mid_sign == 0:
                low = high = mid
                break
            if low_sign == 0 or mid_sign == low_sign:
                low = mid
                low_sign = mid_sign
            else:
                high = mid
                high_sign = mid_sign
        hidden_amount0_in = int(high.to_integral_value())
        if hidden_amount0_in <= 0:
            return None
        hidden_amount1_out = self.swap_expected_out_attos(
            'SellToken0',
            reserve0,
            reserve1,
            hidden_amount0_in,
            0,
        )
        if hidden_amount1_out is None or hidden_amount1_out <= 0 or hidden_amount1_out >= reserve1:
            return None
        return {
            'transaction_id': None,
            'transaction_type': 'SellToken0',
            'from_account': None,
            'amount_0_in': self.from_attos(hidden_amount0_in),
            'amount_0_out': None,
            'amount_1_in': None,
            'amount_1_out': self.from_attos(hidden_amount1_out),
            'liquidity': None,
            'created_at': tx.get('created_at'),
            'synthetic_hidden_swap': True,
        }

    def _decimal_sign(self, value: Decimal) -> int:
        if value > 0:
            return 1
        if value < 0:
            return -1
        return 0

    def _swap_out_within_tolerance(self, left: int, right: int) -> bool:
        return abs(left - right) <= self.swap_out_tolerance_attos
