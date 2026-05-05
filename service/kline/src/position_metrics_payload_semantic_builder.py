from decimal import Decimal


class PositionMetricsPayloadSemanticBuilder:
    def __init__(
        self,
        *,
        build_partial_metrics,
        account_payload_to_string,
    ):
        self.build_partial_metrics = build_partial_metrics
        self.account_payload_to_string = account_payload_to_string

    def build(
        self,
        *,
        position: dict,
        payload_data: dict,
    ) -> dict:
        liquidity = payload_data.get('liquidity') or {}
        liquidity_value = liquidity.get('liquidity')
        total_supply_value = payload_data.get('totalSupply')
        virtual_initial_liquidity = bool(payload_data.get('virtualInitialLiquidity'))
        owner_is_fee_to = (
            self.account_payload_to_string((payload_data.get('pool') or {}).get('fee_to')) == position['owner']
        )
        partial_metrics = self.build_partial_metrics(
            liquidity,
            total_supply_value,
            virtual_initial_liquidity,
        )
        if liquidity_value is not None and total_supply_value not in (None, '0'):
            partial_metrics['exact_share_ratio'] = str(
                (Decimal(str(liquidity_value)) / Decimal(str(total_supply_value))).normalize()
            )
        partial_metrics['owner_is_fee_to'] = owner_is_fee_to
        return partial_metrics
