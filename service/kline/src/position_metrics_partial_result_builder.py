class PositionMetricsPartialResultBuilder:
    def build(
        self,
        liquidity: dict,
        total_supply_value,
        virtual_initial_liquidity: bool,
    ) -> dict:
        return {
            'position_liquidity': liquidity.get('liquidity'),
            'current_total_supply': total_supply_value,
            'exact_share_ratio': None,
            'redeemable_amount0': liquidity.get('amount0'),
            'redeemable_amount1': liquidity.get('amount1'),
            'virtual_initial_liquidity': virtual_initial_liquidity,
            'metrics_status': 'partial_projected_redeemable_only',
            'fee_calculation_complete': False,
            'principal_calculation_complete': False,
            'owner_receives_protocol_fees': False,
            'computation_blockers': [],
            'principal_amount0': None,
            'principal_amount1': None,
            'fee_amount0': '0',
            'fee_amount1': '0',
            'protocol_fee_amount0': '0',
            'protocol_fee_amount1': '0',
            'value_warning_codes': [],
            'value_warning_message': None,
        }
