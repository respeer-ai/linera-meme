class PositionMetricsPartialResultBuilder:
    def build(
        self,
        liquidity: dict,
        total_supply_value,
        virtual_initial_liquidity: bool,
    ) -> dict:
        return {
            'position_liquidity_live': liquidity.get('liquidity'),
            'total_supply_live': total_supply_value,
            'exact_share_ratio': None,
            'redeemable_amount0': liquidity.get('amount0'),
            'redeemable_amount1': liquidity.get('amount1'),
            'virtual_initial_liquidity': virtual_initial_liquidity,
            'metrics_status': 'partial_live_redeemable_only',
            'exact_fee_supported': False,
            'exact_principal_supported': False,
            'owner_is_fee_to': False,
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
