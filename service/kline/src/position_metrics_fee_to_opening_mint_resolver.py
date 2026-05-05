from decimal import Decimal


class PositionMetricsFeeToOpeningMintResolver:
    def __init__(
        self,
        *,
        history_liquidity_before,
        split_protocol_fee_redeemable_attos,
        from_attos,
        epsilon,
    ):
        self.history_liquidity_before = history_liquidity_before
        self.split_protocol_fee_redeemable_attos = split_protocol_fee_redeemable_attos
        self.from_attos = from_attos
        self.epsilon = epsilon

    def resolve(
        self,
        *,
        liquidity_history: list[dict],
        latest_position_tx: dict,
        owner_is_fee_to: bool,
        precheck_context: dict,
    ) -> tuple[dict | None, list[str]]:
        fee_to_opening_mint_case = False
        liquidity_basis = precheck_context['live_liquidity']
        protocol_fee_amount0 = Decimal('0')
        protocol_fee_amount1 = Decimal('0')
        if (
            precheck_context['live_liquidity'] is not None
            and precheck_context['live_liquidity'] - precheck_context['history_liquidity'] > self.epsilon
        ):
            prior_history_liquidity = self.history_liquidity_before(liquidity_history, latest_position_tx)
            fee_to_opening_mint_case = (
                owner_is_fee_to
                and latest_position_tx.get('transaction_type') == 'AddLiquidity'
                and abs(prior_history_liquidity) <= self.epsilon
            )
            if not fee_to_opening_mint_case:
                return None, ['liquidity_history_mismatch']
            liquidity_basis = precheck_context['history_liquidity']
            protocol_fee_amount0_attos, protocol_fee_amount1_attos = self.split_protocol_fee_redeemable_attos(
                redeemable_amount0=precheck_context['redeemable_amount0'],
                redeemable_amount1=precheck_context['redeemable_amount1'],
                live_liquidity=precheck_context['live_liquidity'],
                history_liquidity=precheck_context['history_liquidity'],
            )
            protocol_fee_amount0 = self.from_attos(protocol_fee_amount0_attos) or Decimal('0')
            protocol_fee_amount1 = self.from_attos(protocol_fee_amount1_attos) or Decimal('0')
        return {
            'fee_to_opening_mint_case': fee_to_opening_mint_case,
            'liquidity_basis': liquidity_basis,
            'protocol_fee_amount0': protocol_fee_amount0,
            'protocol_fee_amount1': protocol_fee_amount1,
        }, []
