from decimal import Decimal
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot


class PositionMetricsSnapshotFastPathExactCaseResolver:
    def __init__(
        self,
        *,
        materialized_exact_current_principal_case,
    ):
        self.materialized_exact_current_principal_case = materialized_exact_current_principal_case

    def resolve(
        self,
        *,
        position_basis_snapshot,
        owner_receives_protocol_fees: bool,
        last_transaction_id: int | None,
        basis_transaction_id: int | None,
        fee_free_basis_transaction_id: int | None,
        liquidity_value: Decimal | None,
        tracked_liquidity_value: Decimal | None,
    ) -> str:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        fee_to_opening_mint = (
            owner_receives_protocol_fees
            and liquidity_value is not None
            and tracked_liquidity_value is not None
            and liquidity_value > tracked_liquidity_value
        )
        post_basis_liquidity_changes = (
            fee_free_basis_transaction_id is not None
            and basis_transaction_id is not None
            and fee_free_basis_transaction_id != basis_transaction_id
        )
        no_post_basis_transactions = last_transaction_id == basis_transaction_id
        materialized_case = self.materialized_exact_current_principal_case(position_basis_snapshot)
        if fee_to_opening_mint and post_basis_liquidity_changes:
            if materialized_case is not None:
                return materialized_case.replace(
                    'post_basis_liquidity_changes_with_intervening_swaps',
                    'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
                ).replace(
                    'post_basis_liquidity_changes_without_intervening_swaps',
                    'fee_to_opening_mint_post_basis_liquidity_changes_without_intervening_swaps',
                )
            return 'fee_to_opening_mint_post_basis_liquidity_changes'
        if materialized_case is not None:
            return materialized_case
        if post_basis_liquidity_changes:
            return 'post_basis_liquidity_changes'
        if fee_to_opening_mint and no_post_basis_transactions:
            return 'fee_to_opening_mint_no_post_basis_transactions'
        if fee_to_opening_mint:
            return 'fee_to_opening_mint_post_basis_swaps'
        if no_post_basis_transactions:
            return 'no_post_basis_transactions'
        return 'post_basis_swaps'

    def _position_basis_snapshot(self, snapshot) -> PositionMetricsPositionBasisSnapshot:
        if isinstance(snapshot, PositionMetricsPositionBasisSnapshot):
            return snapshot
        return PositionMetricsPositionBasisSnapshot(snapshot)
