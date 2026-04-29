from decimal import Decimal


class PositionMetricsLiquidityHistoryAnalyzer:
    def __init__(
        self,
        *,
        to_decimal,
        to_attos,
        from_attos,
        normalize_non_negative,
        serialize_decimal,
        split_protocol_fee_redeemable_attos,
        fee_numerator: int,
        fee_denominator: int,
    ):
        self.to_decimal = to_decimal
        self.to_attos = to_attos
        self.from_attos = from_attos
        self.normalize_non_negative = normalize_non_negative
        self.serialize_decimal = serialize_decimal
        self.split_protocol_fee_redeemable_attos = split_protocol_fee_redeemable_attos
        self.fee_numerator = fee_numerator
        self.fee_denominator = fee_denominator

    def history_liquidity(self, liquidity_history: list[dict]) -> Decimal:
        current_liquidity = Decimal('0')
        for row in liquidity_history:
            liquidity = self.to_decimal(row.get('liquidity')) or Decimal('0')
            if row.get('transaction_type') == 'AddLiquidity':
                current_liquidity += liquidity
            elif row.get('transaction_type') == 'RemoveLiquidity':
                current_liquidity -= liquidity
        return current_liquidity

    def latest_position_liquidity_tx(self, liquidity_history: list[dict]) -> dict | None:
        if not liquidity_history:
            return None
        return max(
            liquidity_history,
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
            ),
        )

    def history_liquidity_before(
        self,
        liquidity_history: list[dict],
        latest_position_tx: dict,
    ) -> Decimal:
        current_liquidity = Decimal('0')
        latest_created_at = int(latest_position_tx.get('created_at') or 0)
        latest_transaction_id = int(latest_position_tx.get('transaction_id') or 0)
        for row in liquidity_history:
            row_created_at = int(row.get('created_at') or 0)
            row_transaction_id = int(row.get('transaction_id') or 0)
            if (row_created_at, row_transaction_id) >= (latest_created_at, latest_transaction_id):
                break
            liquidity = self.to_decimal(row.get('liquidity')) or Decimal('0')
            if row.get('transaction_type') == 'AddLiquidity':
                current_liquidity += liquidity
            elif row.get('transaction_type') == 'RemoveLiquidity':
                current_liquidity -= liquidity
        return current_liquidity

    def build_observed_swap_fee_estimate(
        self,
        *,
        pool_transaction_history: list[dict] | None,
        latest_position_tx: dict | None,
        liquidity_basis: Decimal,
        total_supply_live: Decimal,
    ) -> tuple[Decimal, Decimal]:
        if not pool_transaction_history or latest_position_tx is None:
            return Decimal('0'), Decimal('0')
        if liquidity_basis <= Decimal('0') or total_supply_live <= Decimal('0'):
            return Decimal('0'), Decimal('0')
        latest_created_at = int(latest_position_tx.get('created_at') or 0)
        latest_transaction_id = int(latest_position_tx.get('transaction_id') or 0)
        share_ratio = liquidity_basis / total_supply_live
        fee_rate = Decimal(self.fee_denominator - self.fee_numerator) / Decimal(self.fee_denominator)
        observed_fee0 = Decimal('0')
        observed_fee1 = Decimal('0')
        for tx in pool_transaction_history:
            tx_key = (
                int(tx.get('created_at') or 0),
                int(tx.get('transaction_id') or 0),
            )
            if tx_key < (latest_created_at, latest_transaction_id):
                continue
            tx_type = tx.get('transaction_type')
            if tx_type == 'SellToken0':
                amount0_in = self.to_decimal(tx.get('amount_0_in')) or Decimal('0')
                if amount0_in > Decimal('0'):
                    observed_fee0 += amount0_in * fee_rate * share_ratio
            elif tx_type == 'BuyToken0':
                amount1_in = self.to_decimal(tx.get('amount_1_in')) or Decimal('0')
                if amount1_in > Decimal('0'):
                    observed_fee1 += amount1_in * fee_rate * share_ratio
        return observed_fee0, observed_fee1

    def build_estimated_metrics_from_liquidity_history(
        self,
        partial_metrics: dict,
        *,
        liquidity_history: list[dict],
        pool_transaction_history: list[dict] | None,
        live_liquidity: Decimal | None,
        history_liquidity: Decimal,
    ) -> dict:
        redeemable_amount0 = self.to_decimal(partial_metrics['redeemable_amount0'])
        redeemable_amount1 = self.to_decimal(partial_metrics['redeemable_amount1'])
        if redeemable_amount0 is None or redeemable_amount1 is None:
            return partial_metrics
        has_token_amount_history = any(
            row.get('amount_0_in') is not None
            or row.get('amount_0_out') is not None
            or row.get('amount_1_in') is not None
            or row.get('amount_1_out') is not None
            for row in liquidity_history
        )
        if not has_token_amount_history:
            return partial_metrics
        protocol_fee_amount0 = Decimal('0')
        protocol_fee_amount1 = Decimal('0')
        if live_liquidity is not None and live_liquidity > history_liquidity > Decimal('0'):
            protocol_fee_amount0_attos, protocol_fee_amount1_attos = self.split_protocol_fee_redeemable_attos(
                redeemable_amount0=redeemable_amount0,
                redeemable_amount1=redeemable_amount1,
                live_liquidity=live_liquidity,
                history_liquidity=history_liquidity,
            )
            protocol_fee_amount0 = self.from_attos(protocol_fee_amount0_attos) or Decimal('0')
            protocol_fee_amount1 = self.from_attos(protocol_fee_amount1_attos) or Decimal('0')
        redeemable_ex_protocol0 = self.normalize_non_negative(redeemable_amount0 - protocol_fee_amount0)
        redeemable_ex_protocol1 = self.normalize_non_negative(redeemable_amount1 - protocol_fee_amount1)
        total_supply_live = self.to_decimal(partial_metrics.get('total_supply_live')) or Decimal('0')
        latest_position_tx = self.latest_position_liquidity_tx(liquidity_history)
        liquidity_basis = min(history_liquidity, live_liquidity or history_liquidity)
        observed_fee0, observed_fee1 = self.build_observed_swap_fee_estimate(
            pool_transaction_history=pool_transaction_history,
            latest_position_tx=latest_position_tx,
            liquidity_basis=liquidity_basis,
            total_supply_live=total_supply_live,
        )
        fee_amount0 = min(redeemable_ex_protocol0, self.normalize_non_negative(observed_fee0))
        fee_amount1 = min(redeemable_ex_protocol1, self.normalize_non_negative(observed_fee1))
        principal_amount0 = self.normalize_non_negative(redeemable_ex_protocol0 - fee_amount0)
        principal_amount1 = self.normalize_non_negative(redeemable_ex_protocol1 - fee_amount1)
        partial_metrics['metrics_status'] = 'estimated_live_redeemable_with_history'
        partial_metrics['principal_amount0'] = self.serialize_decimal(principal_amount0)
        partial_metrics['principal_amount1'] = self.serialize_decimal(principal_amount1)
        partial_metrics['fee_amount0'] = self.serialize_decimal(fee_amount0)
        partial_metrics['fee_amount1'] = self.serialize_decimal(fee_amount1)
        partial_metrics['protocol_fee_amount0'] = self.serialize_decimal(protocol_fee_amount0)
        partial_metrics['protocol_fee_amount1'] = self.serialize_decimal(protocol_fee_amount1)
        return partial_metrics
