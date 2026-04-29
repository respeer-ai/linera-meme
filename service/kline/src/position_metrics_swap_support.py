class PositionMetricsSwapSupport:
    def __init__(
        self,
        *,
        default_support_factory,
        support_factory,
    ):
        self.default_support_factory = default_support_factory
        self.support_factory = support_factory

    def mint_fee_attos(self, total_supply: int, reserve0: int, reserve1: int, k_last: int) -> int:
        return self.default_support_factory().mint_fee_attos(total_supply, reserve0, reserve1, k_last)

    def sqrt_attos_product(self, amount0: int | None, amount1: int | None) -> int | None:
        return self.default_support_factory().sqrt_attos_product(amount0, amount1)

    def swap_expected_out_attos(
        self,
        tx_type: str,
        reserve0: int,
        reserve1: int,
        amount0_in: int,
        amount1_in: int,
        *,
        fee_numerator: int,
        fee_denominator: int,
    ) -> int | None:
        return self.support_factory(
            swap_fee_numerator=fee_numerator,
            swap_fee_denominator=fee_denominator,
        ).swap_expected_out_attos(tx_type, reserve0, reserve1, amount0_in, amount1_in)

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
        return self.default_support_factory().apply_recorded_swap_attos(
            tx_type,
            reserve0,
            reserve1,
            amount0_in=amount0_in,
            amount0_out=amount0_out,
            amount1_in=amount1_in,
            amount1_out=amount1_out,
        )

    def infer_hidden_swap_before_batch(
        self,
        reserve0: int,
        reserve1: int,
        pool_transaction_history: list[dict],
        index: int,
    ) -> dict | None:
        return self.default_support_factory().infer_hidden_swap_before_batch(
            reserve0,
            reserve1,
            pool_transaction_history,
            index,
        )
