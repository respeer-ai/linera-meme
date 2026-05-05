class PositionMetricsNoSwapExactResolver:
    def __init__(self, *, serialize_decimal):
        self.serialize_decimal = serialize_decimal

    def resolve(
        self,
        partial_metrics: dict,
        *,
        redeemable_amount0,
        redeemable_amount1,
        blockers: list[str],
    ) -> dict:
        partial_metrics['metrics_status'] = 'exact_no_swap_history'
        partial_metrics['exact_fee_supported'] = True
        partial_metrics['exact_principal_supported'] = True
        partial_metrics['principal_amount0'] = self.serialize_decimal(redeemable_amount0)
        partial_metrics['principal_amount1'] = self.serialize_decimal(redeemable_amount1)
        partial_metrics['fee_amount0'] = '0'
        partial_metrics['fee_amount1'] = '0'
        partial_metrics['protocol_fee_amount0'] = '0'
        partial_metrics['protocol_fee_amount1'] = '0'
        partial_metrics['computation_blockers'] = list(blockers)
        return partial_metrics
