from decimal import Decimal
from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot


class PositionMetricsSnapshotFastPathEligibility:
    def __init__(
        self,
        *,
        to_decimal,
        decimal_equal,
        int_or_none,
        tracked_liquidity_value,
        payload_tracked_liquidity_value,
        materialized_exact_current_principal_case,
        basis_opens_current_round,
        current_round_trade_count_before_basis,
        trade_count_between_basis_and_fee_free_basis,
        eligible_fee_to_opening_mint_case,
        safe_current_owner_protocol_fee_component_proven,
    ):
        self.to_decimal = to_decimal
        self.decimal_equal = decimal_equal
        self.int_or_none = int_or_none
        self.tracked_liquidity_value = tracked_liquidity_value
        self.payload_tracked_liquidity_value = payload_tracked_liquidity_value
        self.materialized_exact_current_principal_case = materialized_exact_current_principal_case
        self.basis_opens_current_round = basis_opens_current_round
        self.current_round_trade_count_before_basis = current_round_trade_count_before_basis
        self.trade_count_between_basis_and_fee_free_basis = trade_count_between_basis_and_fee_free_basis
        self.eligible_fee_to_opening_mint_case = eligible_fee_to_opening_mint_case
        self.safe_current_owner_protocol_fee_component_proven = safe_current_owner_protocol_fee_component_proven

    def is_eligible(
        self,
        *,
        position: dict,
        payload: dict,
        position_basis_snapshot: dict | None,
        pool_state_snapshot: dict | None,
    ) -> bool:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        pool_state_snapshot = self._pool_state_snapshot(pool_state_snapshot)
        if position_basis_snapshot.raw() is None or pool_state_snapshot.raw() is None:
            return False
        if str(position.get('status') or 'active') != 'active':
            return False
        if str(position_basis_snapshot.status() or '') != 'active':
            return False
        basis_type = str(position_basis_snapshot.basis_type() or '')
        if basis_type not in {'add_liquidity', 'remove_liquidity'}:
            return False
        if (
            basis_type == 'add_liquidity'
            and not self._opened_at_matches_current_round_basis(
                position=position,
                position_basis_snapshot=position_basis_snapshot,
            )
        ):
            return False
        if not self._fee_free_basis_compatible(
            position_basis_snapshot=position_basis_snapshot,
            pool_state_snapshot=pool_state_snapshot,
        ):
            return False
        liquidity = (payload.get('data') or {}).get('liquidity') or {}
        current_liquidity = self.to_decimal(liquidity.get('liquidity'))
        if current_liquidity is None:
            return False
        if self.to_decimal((payload.get('data') or {}).get('totalSupply')) is None:
            return False
        if self.to_decimal(liquidity.get('amount0')) is None or self.to_decimal(liquidity.get('amount1')) is None:
            return False
        if self.to_decimal(position.get('current_liquidity')) is None:
            return False
        tracked_liquidity = self.payload_tracked_liquidity_value(
            position=position,
            payload=payload,
            position_basis_snapshot=position_basis_snapshot,
        )
        if tracked_liquidity is None:
            return False
        current_liquidity_allowed = self.decimal_equal(position.get('current_liquidity'), liquidity.get('liquidity'))
        if (
            not current_liquidity_allowed
            and not self.eligible_fee_to_opening_mint_case(
                position=position,
                payload=payload,
                position_basis_snapshot=position_basis_snapshot,
                tracked_liquidity=tracked_liquidity,
                current_liquidity=current_liquidity,
            )
            and not self.safe_current_owner_protocol_fee_component_proven(
                position_basis_snapshot=position_basis_snapshot,
                current_liquidity=current_liquidity,
                tracked_liquidity=tracked_liquidity,
            )
        ):
            return False
        return True

    def _opened_at_matches_current_round_basis(
        self,
        *,
        position: dict,
        position_basis_snapshot: dict,
    ) -> bool:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        opened_at = self.int_or_none(position.get('opened_at'))
        basis_time_ms = self.int_or_none(position_basis_snapshot.basis_time_ms())
        if opened_at == basis_time_ms:
            return True
        if self.materialized_exact_current_principal_case(position_basis_snapshot) is not None:
            return True
        if opened_at is None or basis_time_ms is None or opened_at > basis_time_ms:
            return False
        return (
            self.basis_opens_current_round(position_basis_snapshot)
            or self.current_round_trade_count_before_basis(position_basis_snapshot) == 0
        )

    def _fee_free_basis_compatible(
        self,
        *,
        position_basis_snapshot: dict,
        pool_state_snapshot: dict,
    ) -> bool:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        pool_state_snapshot = self._pool_state_snapshot(pool_state_snapshot)
        basis_transaction_id = self.int_or_none(position_basis_snapshot.basis_transaction_id())
        basis_time_ms = self.int_or_none(position_basis_snapshot.basis_time_ms())
        fee_free_basis_transaction_id = self.int_or_none(pool_state_snapshot.fee_free_basis_transaction_id())
        fee_free_basis_time_ms = self.int_or_none(pool_state_snapshot.fee_free_basis_time_ms())
        if (
            basis_transaction_id == fee_free_basis_transaction_id
            and basis_time_ms == fee_free_basis_time_ms
        ):
            return True
        if fee_free_basis_transaction_id is None or fee_free_basis_time_ms is None:
            return False
        if basis_transaction_id is None or basis_time_ms is None:
            return False
        if (basis_time_ms, basis_transaction_id) >= (fee_free_basis_time_ms, fee_free_basis_transaction_id):
            return False
        if self.materialized_exact_current_principal_case(position_basis_snapshot) is not None:
            return True
        return self.trade_count_between_basis_and_fee_free_basis(position_basis_snapshot) == 0

    def _position_basis_snapshot(self, snapshot) -> PositionMetricsPositionBasisSnapshot:
        if isinstance(snapshot, PositionMetricsPositionBasisSnapshot):
            return snapshot
        return PositionMetricsPositionBasisSnapshot(snapshot)

    def _pool_state_snapshot(self, snapshot) -> PositionMetricsPoolStateSnapshot:
        if isinstance(snapshot, PositionMetricsPoolStateSnapshot):
            return snapshot
        return PositionMetricsPoolStateSnapshot(snapshot)
