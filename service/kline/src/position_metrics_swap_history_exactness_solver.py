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
        owner_receives_protocol_fees: bool,
    ) -> tuple[dict | None, list[str]]:
        validation_context, blockers = self.validator.validate(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            owner_receives_protocol_fees=owner_receives_protocol_fees,
        )
        if blockers:
            return None, blockers
        return self.materializer.materialize(
            partial_metrics,
            validation_context=validation_context,
        )
