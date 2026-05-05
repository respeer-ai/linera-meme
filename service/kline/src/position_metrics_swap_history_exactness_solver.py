class PositionMetricsSwapHistoryExactnessSolver:
    def __init__(
        self,
        *,
        validator,
        materializer,
    ):
        self.validator = validator
        self.materializer = materializer

    def solve(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict],
        pool_transaction_history: list[dict] | None,
        owner_is_fee_to: bool,
    ) -> tuple[dict | None, list[str]]:
        validation_context, blockers = self.validator.validate(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            owner_is_fee_to=owner_is_fee_to,
        )
        if blockers:
            return None, blockers
        return self.materializer.materialize(
            partial_metrics,
            validation_context=validation_context,
        )
