class PositionMetricsSwapHistoryExactMaterializer:
    def __init__(
        self,
        *,
        from_attos,
        normalize_non_negative,
        serialize_decimal,
    ):
        self.from_attos = from_attos
        self.normalize_non_negative = normalize_non_negative
        self.serialize_decimal = serialize_decimal

    def materialize(
        self,
        partial_metrics: dict,
        *,
        validation_context: dict,
    ) -> tuple[dict | None, list[str]]:
        principal_amount0 = self.from_attos(
            validation_context['liquidity_basis_attos'] * validation_context['fee_free_state']['reserve0']
            // validation_context['current_total_supply_attos']
        )
        principal_amount1 = self.from_attos(
            validation_context['liquidity_basis_attos'] * validation_context['fee_free_state']['reserve1']
            // validation_context['current_total_supply_attos']
        )
        fee_amount0 = self.normalize_non_negative(
            validation_context['redeemable_amount0']
            - validation_context['protocol_fee_amount0']
            - principal_amount0
        )
        fee_amount1 = self.normalize_non_negative(
            validation_context['redeemable_amount1']
            - validation_context['protocol_fee_amount1']
            - principal_amount1
        )

        if fee_amount0 < 0 or fee_amount1 < 0:
            return None, ['fee_simulation_exceeds_projected_redeemable']

        partial_metrics['metrics_status'] = 'exact_swap_history_no_post_open_liquidity_changes'
        partial_metrics['fee_calculation_complete'] = True
        partial_metrics['principal_calculation_complete'] = True
        partial_metrics['principal_amount0'] = self.serialize_decimal(principal_amount0)
        partial_metrics['principal_amount1'] = self.serialize_decimal(principal_amount1)
        partial_metrics['fee_amount0'] = self.serialize_decimal(fee_amount0)
        partial_metrics['fee_amount1'] = self.serialize_decimal(fee_amount1)
        partial_metrics['protocol_fee_amount0'] = self.serialize_decimal(validation_context['protocol_fee_amount0'])
        partial_metrics['protocol_fee_amount1'] = self.serialize_decimal(validation_context['protocol_fee_amount1'])
        partial_metrics['computation_blockers'] = []
        return partial_metrics, []
