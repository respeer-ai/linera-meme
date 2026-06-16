from decimal import Decimal, InvalidOperation


class PositionMetricsValueSupport:
    def __init__(
        self,
        *,
        attos_scale: int,
        display_quantum: Decimal,
        epsilon: Decimal,
        liquidity_mint_tolerance_attos: int,
        swap_out_tolerance_attos: int,
    ):
        self.attos_scale = attos_scale
        self.display_quantum = display_quantum
        self.epsilon = epsilon
        self.liquidity_mint_tolerance_attos = liquidity_mint_tolerance_attos
        self.swap_out_tolerance_attos = swap_out_tolerance_attos

    def to_decimal(self, value):
        if value is None:
            return None
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None

    def serialize_decimal(self, value: Decimal | None):
        if value is None:
            return None
        try:
            if value == 0:
                return '0'
            return format(value.quantize(self.display_quantum).normalize(), 'f')
        except (InvalidOperation, ValueError):
            return '0'

    def to_attos(self, value) -> int | None:
        if value is None:
            return None
        try:
            return int(Decimal(str(value)) * self.attos_scale)
        except (InvalidOperation, ValueError):
            return None

    def from_attos(self, value: int | None) -> Decimal | None:
        if value is None:
            return None
        try:
            return Decimal(value) / Decimal(self.attos_scale)
        except (InvalidOperation, ValueError):
            return None

    def attos_within_tolerance(
        self,
        left: int,
        right: int,
        tolerance: int | None = None,
    ) -> bool:
        effective_tolerance = (
            self.liquidity_mint_tolerance_attos if tolerance is None else tolerance
        )
        return abs(left - right) <= effective_tolerance

    def swap_out_within_tolerance(
        self,
        left: int,
        right: int,
        tolerance: int | None = None,
    ) -> bool:
        effective_tolerance = (
            self.swap_out_tolerance_attos if tolerance is None else tolerance
        )
        return abs(left - right) <= effective_tolerance

    def normalize_non_negative(self, value: Decimal, tolerance: Decimal | None = None) -> Decimal:
        effective_tolerance = self.epsilon if tolerance is None else tolerance
        if abs(value) <= effective_tolerance:
            return Decimal('0')
        return value

    def is_close(
        self,
        left: Decimal | None,
        right: Decimal | None,
        tolerance: Decimal | None = None,
    ) -> bool:
        if left is None or right is None:
            return False
        effective_tolerance = self.epsilon if tolerance is None else tolerance
        return abs(left - right) <= effective_tolerance

    def split_protocol_fee_redeemable_attos(
        self,
        *,
        redeemable_amount0: Decimal,
        redeemable_amount1: Decimal,
        current_liquidity: Decimal,
        history_liquidity: Decimal,
    ) -> tuple[int, int]:
        redeemable_amount0_attos = self.to_attos(redeemable_amount0) or 0
        redeemable_amount1_attos = self.to_attos(redeemable_amount1) or 0
        current_liquidity_attos = self.to_attos(current_liquidity) or 0
        history_liquidity_attos = self.to_attos(history_liquidity) or 0
        protocol_fee_liquidity_attos = max(current_liquidity_attos - history_liquidity_attos, 0)

        if protocol_fee_liquidity_attos == 0 or current_liquidity_attos == 0:
            return 0, 0

        return (
            redeemable_amount0_attos * protocol_fee_liquidity_attos // current_liquidity_attos,
            redeemable_amount1_attos * protocol_fee_liquidity_attos // current_liquidity_attos,
        )

    def history_net_token_amounts(self, liquidity_history: list[dict]) -> tuple[Decimal, Decimal]:
        amount0 = Decimal('0')
        amount1 = Decimal('0')
        for row in liquidity_history:
            liquidity = self.to_decimal(row.get('liquidity')) or Decimal('0')
            if liquidity <= Decimal('0'):
                continue
            if row.get('transaction_type') == 'AddLiquidity':
                amount0 += self.to_decimal(row.get('amount_0_in')) or Decimal('0')
                amount1 += self.to_decimal(row.get('amount_1_in')) or Decimal('0')
            elif row.get('transaction_type') == 'RemoveLiquidity':
                amount0 -= self.to_decimal(row.get('amount_0_out')) or Decimal('0')
                amount1 -= self.to_decimal(row.get('amount_1_out')) or Decimal('0')
        return amount0, amount1
