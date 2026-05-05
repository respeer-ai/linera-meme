class PositionMetricsSwapHistoryExactnessValidator:
    def __init__(
        self,
        *,
        precheck,
        alignment_checker,
    ):
        self.precheck = precheck
        self.alignment_checker = alignment_checker

    def validate(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict],
        pool_transaction_history: list[dict] | None,
        owner_is_fee_to: bool,
    ) -> tuple[dict | None, list[str]]:
        precheck_context, blockers = self.precheck.check(
            partial_metrics,
            liquidity_history=liquidity_history,
        )
        if blockers:
            return None, blockers
        return self.alignment_checker.check(
            partial_metrics,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            owner_is_fee_to=owner_is_fee_to,
            precheck_context=precheck_context,
        )
