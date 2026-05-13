from decimal import Decimal
from account_codec import AccountCodec
from query.read_models.position_metrics_protocol_fee_split_semantics import PositionMetricsProtocolFeeSplitSemantics
from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot
from query.read_models.position_metrics_snapshot_fast_path_exact_case_resolver import PositionMetricsSnapshotFastPathExactCaseResolver
from query.read_models.position_metrics_snapshot_fast_path_eligibility import PositionMetricsSnapshotFastPathEligibility
from query.read_models.position_metrics_snapshot_shadow_evaluator import PositionMetricsSnapshotShadowEvaluator
from query.read_models.position_metrics_snapshot_fast_path_result_builder import PositionMetricsSnapshotFastPathResultBuilder


class PositionMetricsSnapshotFastPath:
    def __init__(
        self,
        *,
        display_quantum: Decimal = Decimal('0.000000000000000001'),
        account_codec: AccountCodec | None = None,
        protocol_fee_split_semantics: PositionMetricsProtocolFeeSplitSemantics | None = None,
        snapshot_shadow_evaluator: PositionMetricsSnapshotShadowEvaluator | None = None,
        result_builder: PositionMetricsSnapshotFastPathResultBuilder | None = None,
    ):
        self.display_quantum = display_quantum
        self.account_codec = account_codec or AccountCodec()
        self.protocol_fee_split_semantics = protocol_fee_split_semantics or PositionMetricsProtocolFeeSplitSemantics()
        self.snapshot_shadow_evaluator = snapshot_shadow_evaluator or PositionMetricsSnapshotShadowEvaluator(
            protocol_fee_split_semantics=self.protocol_fee_split_semantics,
        )
        self.result_builder = result_builder or PositionMetricsSnapshotFastPathResultBuilder(
            snapshot_shadow_evaluator=self.snapshot_shadow_evaluator,
        )
        self.exact_case_resolver = PositionMetricsSnapshotFastPathExactCaseResolver(
            materialized_exact_current_principal_case=self._materialized_exact_current_principal_case,
        )
        self.eligibility = PositionMetricsSnapshotFastPathEligibility(
            to_decimal=self._to_decimal,
            decimal_equal=self._decimal_equal,
            int_or_none=self._int_or_none,
            tracked_liquidity_value=self._tracked_liquidity_value,
            materialized_exact_current_principal_case=self._materialized_exact_current_principal_case,
            basis_opens_current_round=self._basis_opens_current_round,
            current_round_trade_count_before_basis=self._current_round_trade_count_before_basis,
            trade_count_between_basis_and_fee_free_basis=self._trade_count_between_basis_and_fee_free_basis,
            eligible_fee_to_opening_mint_case=self._eligible_fee_to_opening_mint_case,
            safe_current_owner_protocol_fee_component_proven=self._safe_current_owner_protocol_fee_component_proven,
        )

    def resolve(
        self,
        *,
        position: dict,
        payload: dict,
        position_basis_snapshot,
        pool_state_snapshot,
    ) -> dict | None:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        pool_state_snapshot = self._pool_state_snapshot(pool_state_snapshot)
        if not self.eligibility.is_eligible(
            position=position,
            payload=payload,
            position_basis_snapshot=position_basis_snapshot,
            pool_state_snapshot=pool_state_snapshot,
        ):
            return None
        data = payload.get('data') or {}
        liquidity = data.get('liquidity') or {}
        liquidity_value = self._to_decimal(liquidity.get('liquidity'))
        total_supply_value = self._to_decimal(data.get('totalSupply'))
        tracked_liquidity_value = self._tracked_liquidity_value(position_basis_snapshot)
        owner_receives_protocol_fees = self._account_payload_to_string((data.get('pool') or {}).get('fee_to')) == position['owner']
        pool_has_fee_to = (data.get('pool') or {}).get('fee_to') is not None
        redeemable_amount0 = self._serialize_decimal(self._to_decimal(liquidity.get('amount0')))
        redeemable_amount1 = self._serialize_decimal(self._to_decimal(liquidity.get('amount1')))
        materialized_protocol_fee_split_case = self._materialized_protocol_fee_split_case(
            position_basis_snapshot=position_basis_snapshot,
            owner_receives_protocol_fees=owner_receives_protocol_fees,
            current_liquidity=liquidity_value,
            tracked_liquidity=tracked_liquidity_value,
        )
        principal_amount0, principal_amount1, fee_amount0, fee_amount1, protocol_fee_amount0, protocol_fee_amount1 = self._principal_and_fee(
            liquidity_value=liquidity_value,
            tracked_liquidity_value=tracked_liquidity_value,
            total_supply_value=total_supply_value,
            redeemable_amount0=self._to_decimal(liquidity.get('amount0')),
            redeemable_amount1=self._to_decimal(liquidity.get('amount1')),
            position_basis_snapshot=position_basis_snapshot,
            pool_state_snapshot=pool_state_snapshot,
            owner_receives_protocol_fees=owner_receives_protocol_fees,
            pool_has_fee_to=pool_has_fee_to,
        )
        if (
            principal_amount0 is None
            or principal_amount1 is None
            or fee_amount0 is None
            or fee_amount1 is None
            or protocol_fee_amount0 is None
            or protocol_fee_amount1 is None
        ):
            return None
        exact_case = self.exact_case_resolver.resolve(
            position_basis_snapshot=position_basis_snapshot,
            owner_receives_protocol_fees=owner_receives_protocol_fees,
            last_transaction_id=self._int_or_none(pool_state_snapshot.last_transaction_id()),
            basis_transaction_id=self._int_or_none(position_basis_snapshot.basis_transaction_id()),
            fee_free_basis_transaction_id=self._int_or_none(pool_state_snapshot.fee_free_basis_transaction_id()),
            liquidity_value=liquidity_value,
            tracked_liquidity_value=tracked_liquidity_value,
        )
        share_ratio = None
        if (
            liquidity_value is not None
            and total_supply_value is not None
            and total_supply_value > Decimal('0')
        ):
            share_ratio = self._serialize_decimal(liquidity_value / total_supply_value)
        projected_metrics = {
            'position_liquidity': self._serialize_decimal(liquidity_value),
            'current_total_supply': self._serialize_decimal(total_supply_value),
            'exact_share_ratio': share_ratio,
            'redeemable_amount0': redeemable_amount0,
            'redeemable_amount1': redeemable_amount1,
            'virtual_initial_liquidity': bool(data.get('virtualInitialLiquidity')),
            'metrics_status': 'exact_no_swap_history',
            'fee_calculation_complete': True,
            'principal_calculation_complete': True,
            'owner_receives_protocol_fees': owner_receives_protocol_fees,
            'computation_blockers': [],
            'principal_amount0': self._serialize_decimal(principal_amount0),
            'principal_amount1': self._serialize_decimal(principal_amount1),
            'fee_amount0': self._serialize_decimal(fee_amount0),
            'fee_amount1': self._serialize_decimal(fee_amount1),
            'protocol_fee_amount0': self._serialize_decimal(protocol_fee_amount0),
            'protocol_fee_amount1': self._serialize_decimal(protocol_fee_amount1),
            'value_warning_codes': [],
            'value_warning_message': None,
        }
        return self.result_builder.build(
            position=position,
            projected_metrics=projected_metrics,
            exact_case=exact_case,
            position_basis_snapshot=position_basis_snapshot,
            pool_state_snapshot=pool_state_snapshot,
        )

    def _principal_and_fee(
        self,
        *,
        liquidity_value: Decimal | None,
        tracked_liquidity_value: Decimal | None,
        total_supply_value: Decimal | None,
        redeemable_amount0: Decimal | None,
        redeemable_amount1: Decimal | None,
        position_basis_snapshot,
        pool_state_snapshot,
        owner_receives_protocol_fees: bool,
        pool_has_fee_to: bool,
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None, Decimal | None, Decimal | None, Decimal | None]:
        if (
            liquidity_value is None
            or tracked_liquidity_value is None
            or total_supply_value is None
            or total_supply_value <= Decimal('0')
            or redeemable_amount0 is None
            or redeemable_amount1 is None
        ):
            return None, None, None, None, None, None
        protocol_fee_amount0, protocol_fee_amount1, liquidity_basis = self._protocol_fee_split(
            owner_receives_protocol_fees=owner_receives_protocol_fees,
            position_basis_snapshot=position_basis_snapshot,
            current_liquidity=liquidity_value,
            tracked_liquidity=tracked_liquidity_value,
            redeemable_amount0=redeemable_amount0,
            redeemable_amount1=redeemable_amount1,
        )
        if protocol_fee_amount0 is None or protocol_fee_amount1 is None or liquidity_basis is None:
            return None, None, None, None, None, None
        materialized_principal_amount0 = None
        materialized_principal_amount1 = None
        if self._materialized_current_principal_allowed(
            position_basis_snapshot=position_basis_snapshot,
            pool_has_fee_to=pool_has_fee_to,
            owner_receives_protocol_fees=owner_receives_protocol_fees,
            current_liquidity=liquidity_value,
            tracked_liquidity=tracked_liquidity_value,
        ):
            materialized_principal_amount0 = self._materialized_principal_amount_current(
                position_basis_snapshot,
                'principal_amount_0_current',
            )
            materialized_principal_amount1 = self._materialized_principal_amount_current(
                position_basis_snapshot,
                'principal_amount_1_current',
            )
        if materialized_principal_amount0 is not None and materialized_principal_amount1 is not None:
            fee_amount0 = self._normalize_non_negative(
                redeemable_amount0 - protocol_fee_amount0 - materialized_principal_amount0
            )
            fee_amount1 = self._normalize_non_negative(
                redeemable_amount1 - protocol_fee_amount1 - materialized_principal_amount1
            )
            if fee_amount0 < 0 or fee_amount1 < 0:
                return None, None, None, None, None, None
            return (
                materialized_principal_amount0,
                materialized_principal_amount1,
                fee_amount0,
                fee_amount1,
                protocol_fee_amount0,
                protocol_fee_amount1,
            )
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        pool_state_snapshot = self._pool_state_snapshot(pool_state_snapshot)
        last_transaction_id = self._int_or_none(pool_state_snapshot.last_transaction_id())
        basis_transaction_id = self._int_or_none(position_basis_snapshot.basis_transaction_id())
        if last_transaction_id == basis_transaction_id:
            return (
                self._normalize_non_negative(redeemable_amount0 - protocol_fee_amount0),
                self._normalize_non_negative(redeemable_amount1 - protocol_fee_amount1),
                Decimal('0'),
                Decimal('0'),
                protocol_fee_amount0,
                protocol_fee_amount1,
            )
        fee_free_reserve_0 = self._to_decimal(pool_state_snapshot.fee_free_reserve_0())
        fee_free_reserve_1 = self._to_decimal(pool_state_snapshot.fee_free_reserve_1())
        if fee_free_reserve_0 is None or fee_free_reserve_1 is None:
            return None, None, None, None, None, None
        principal_amount0 = self._normalize_non_negative(liquidity_basis * fee_free_reserve_0 / total_supply_value)
        principal_amount1 = self._normalize_non_negative(liquidity_basis * fee_free_reserve_1 / total_supply_value)
        fee_amount0 = self._normalize_non_negative(redeemable_amount0 - protocol_fee_amount0 - principal_amount0)
        fee_amount1 = self._normalize_non_negative(redeemable_amount1 - protocol_fee_amount1 - principal_amount1)
        if fee_amount0 < 0 or fee_amount1 < 0:
            return None, None, None, None, None, None
        return principal_amount0, principal_amount1, fee_amount0, fee_amount1, protocol_fee_amount0, protocol_fee_amount1

    def _eligible_fee_to_opening_mint_case(
        self,
        *,
        position: dict,
        payload: dict,
        position_basis_snapshot,
        tracked_liquidity: Decimal,
        current_liquidity: Decimal | None,
    ) -> bool:
        if current_liquidity is None or current_liquidity <= tracked_liquidity:
            return False
        if self._account_payload_to_string(((payload.get('data') or {}).get('pool') or {}).get('fee_to')) != position['owner']:
            return False
        if self._materialized_exact_current_principal_case(position_basis_snapshot) is not None:
            return True
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        if str(position_basis_snapshot.basis_type() or '') != 'add_liquidity':
            return False
        if self._prior_liquidity_before_basis(position_basis_snapshot) != Decimal('0'):
            return False
        return True

    def _protocol_fee_split(
        self,
        *,
        owner_receives_protocol_fees: bool,
        position_basis_snapshot,
        current_liquidity: Decimal,
        tracked_liquidity: Decimal,
        redeemable_amount0: Decimal,
        redeemable_amount1: Decimal,
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
        if current_liquidity <= tracked_liquidity:
            return Decimal('0'), Decimal('0'), tracked_liquidity
        if self._safe_current_owner_protocol_fee_component_proven(
            position_basis_snapshot=position_basis_snapshot,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            facts = self._semantic_facts(position_basis_snapshot)
            protocol_fee_liquidity = self._to_decimal(facts.protocol_fee_liquidity_owned_by_current_owner_current())
            if protocol_fee_liquidity is None:
                return None, None, None
            protocol_fee_ratio = protocol_fee_liquidity / current_liquidity
            protocol_fee_amount0 = self._normalize_non_negative(redeemable_amount0 * protocol_fee_ratio)
            protocol_fee_amount1 = self._normalize_non_negative(redeemable_amount1 * protocol_fee_ratio)
            return protocol_fee_amount0, protocol_fee_amount1, tracked_liquidity
        if not owner_receives_protocol_fees:
            return None, None, None
        materialized_protocol_fee_split_case = self._materialized_protocol_fee_split_case(
            position_basis_snapshot=position_basis_snapshot,
            owner_receives_protocol_fees=owner_receives_protocol_fees,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        )
        if (
            self._materialized_exact_current_principal_case(position_basis_snapshot) is not None
            and materialized_protocol_fee_split_case in {
                'fee_to_opening_add_from_zero',
                'fee_to_latest_remove_basis',
                'fee_to_basis_only_nonzero_prior_add_basis',
                'fee_to_continuous_nonzero_prior_add_basis',
            }
        ):
            protocol_fee_liquidity = self._protocol_fee_liquidity_current(
                position_basis_snapshot=position_basis_snapshot,
                current_liquidity=current_liquidity,
                tracked_liquidity=tracked_liquidity,
            )
            if protocol_fee_liquidity is None:
                return None, None, None
            protocol_fee_ratio = protocol_fee_liquidity / current_liquidity
            protocol_fee_amount0 = self._normalize_non_negative(redeemable_amount0 * protocol_fee_ratio)
            protocol_fee_amount1 = self._normalize_non_negative(redeemable_amount1 * protocol_fee_ratio)
            return protocol_fee_amount0, protocol_fee_amount1, tracked_liquidity
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        if str(position_basis_snapshot.basis_type() or '') != 'add_liquidity':
            return None, None, None
        if self._prior_liquidity_before_basis(position_basis_snapshot) != Decimal('0'):
            return None, None, None
        protocol_fee_ratio = (current_liquidity - tracked_liquidity) / current_liquidity
        protocol_fee_amount0 = self._normalize_non_negative(redeemable_amount0 * protocol_fee_ratio)
        protocol_fee_amount1 = self._normalize_non_negative(redeemable_amount1 * protocol_fee_ratio)
        return protocol_fee_amount0, protocol_fee_amount1, tracked_liquidity

    def _tracked_liquidity_value(self, position_basis_snapshot: dict) -> Decimal | None:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        return self._to_decimal(position_basis_snapshot.current_liquidity())

    def _prior_liquidity_before_basis(self, position_basis_snapshot: dict) -> Decimal:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        return self._to_decimal(position_basis_snapshot.prior_liquidity_before_basis()) or Decimal('0')

    def _has_only_zero_liquidity_before_basis(self, position_basis_snapshot: dict) -> bool:
        return self._semantic_facts(position_basis_snapshot).has_only_zero_liquidity_before_basis()

    def _basis_opens_current_round(self, position_basis_snapshot: dict) -> bool:
        return self._semantic_facts(position_basis_snapshot).basis_opens_current_round()

    def _current_round_liquidity_event_count(self, position_basis_snapshot: dict) -> int | None:
        return self._semantic_facts(position_basis_snapshot).current_round_liquidity_event_count()

    def _current_round_started_at(self, position_basis_snapshot: dict) -> int | None:
        return self._semantic_facts(position_basis_snapshot).current_round_started_at()

    def _current_round_started_transaction_id(self, position_basis_snapshot: dict) -> int | None:
        return self._semantic_facts(position_basis_snapshot).current_round_started_transaction_id()

    def _current_round_trade_count_before_basis(self, position_basis_snapshot: dict) -> int | None:
        return self._semantic_facts(position_basis_snapshot).current_round_trade_count_before_basis()

    def _trade_count_between_basis_and_fee_free_basis(self, position_basis_snapshot: dict) -> int | None:
        return self._semantic_facts(position_basis_snapshot).trade_count_between_basis_and_fee_free_basis()

    def _materialized_principal_amount_current(
        self,
        position_basis_snapshot: dict,
        field_name: str,
    ) -> Decimal | None:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        value = {
            'principal_amount_0_current': position_basis_snapshot.principal_amount_0_current(),
            'principal_amount_1_current': position_basis_snapshot.principal_amount_1_current(),
        }[field_name]
        if value in (None, ''):
            return None
        return self._to_decimal(value)

    def _materialized_exact_current_principal_case(self, position_basis_snapshot) -> str | None:
        return self._position_basis_snapshot(position_basis_snapshot).exact_current_principal_case()

    def _materialized_post_basis_remove_count(self, position_basis_snapshot: dict) -> int:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        return position_basis_snapshot.post_basis_remove_count()

    def _materialized_protocol_fee_mint_event_count(self, position_basis_snapshot) -> int | None:
        return self._position_basis_snapshot(position_basis_snapshot).post_basis_protocol_fee_mint_event_count()

    def _materialized_protocol_fee_liquidity_provenance_case(self, position_basis_snapshot) -> str | None:
        return self._position_basis_snapshot(position_basis_snapshot).protocol_fee_liquidity_provenance_case()

    def _materialized_current_owner_protocol_fee_provenance_case(self, position_basis_snapshot) -> str | None:
        return self._position_basis_snapshot(position_basis_snapshot).protocol_fee_current_owner_provenance_case()

    def _protocol_fee_liquidity_current(
        self,
        *,
        position_basis_snapshot: dict,
        current_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> Decimal | None:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        materialized_protocol_fee_split_case = self._materialized_protocol_fee_split_case(
            position_basis_snapshot=position_basis_snapshot,
            owner_receives_protocol_fees=True,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        )
        if materialized_protocol_fee_split_case == 'fee_to_continuous_nonzero_prior_add_basis':
            return self._to_decimal(position_basis_snapshot.fee_to_continuous_protocol_fee_liquidity_current())
        if materialized_protocol_fee_split_case == 'fee_to_basis_only_nonzero_prior_add_basis':
            return self._to_decimal(position_basis_snapshot.basis_protocol_fee_liquidity_minted())
        if materialized_protocol_fee_split_case in {
            'all_protocol_fee_mints_owned_by_current_owner',
            'current_owner_protocol_fee_component_proven',
        }:
            return self._to_decimal(position_basis_snapshot.protocol_fee_liquidity_owned_by_current_owner_current())
        return current_liquidity - tracked_liquidity

    def _safe_all_protocol_fee_mints_owned_by_current_owner(
        self,
        *,
        position_basis_snapshot: dict,
        current_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        if current_liquidity is None or tracked_liquidity is None:
            return False
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        if self._materialized_current_owner_protocol_fee_provenance_case(position_basis_snapshot) != (
            'all_mints_owned_by_current_owner'
        ):
            return False
        owned_by_current_owner = self._to_decimal(position_basis_snapshot.protocol_fee_liquidity_owned_by_current_owner_current())
        owned_by_other_accounts = self._to_decimal(position_basis_snapshot.protocol_fee_liquidity_owned_by_other_accounts())
        owner_unknown = self._to_decimal(position_basis_snapshot.protocol_fee_liquidity_owner_unknown())
        if owned_by_current_owner is None or owned_by_current_owner <= Decimal('0'):
            return False
        if owned_by_other_accounts not in (None, Decimal('0')):
            return False
        if owner_unknown not in (None, Decimal('0')):
            return False
        return self._decimal_equal(current_liquidity, tracked_liquidity + owned_by_current_owner)

    def _safe_current_owner_protocol_fee_component_proven(
        self,
        *,
        position_basis_snapshot: dict,
        current_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        if current_liquidity is None or tracked_liquidity is None:
            return False
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        owned_by_current_owner = self._to_decimal(position_basis_snapshot.protocol_fee_liquidity_owned_by_current_owner_current())
        if owned_by_current_owner is None or owned_by_current_owner <= Decimal('0'):
            return False
        return self._decimal_equal(current_liquidity, tracked_liquidity + owned_by_current_owner)

    def _safe_fee_to_basis_only_nonzero_prior_add_basis(
        self,
        *,
        position_basis_snapshot: dict,
        current_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        if current_liquidity is None or tracked_liquidity is None:
            return False
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        if position_basis_snapshot.fee_to_continuity_known_before_basis() is not True:
            return False
        owner = position_basis_snapshot.fee_to_continuity_owner()
        if owner in (None, ''):
            return False
        if position_basis_snapshot.fee_to_account_at_basis() != owner:
            return False
        if self._materialized_protocol_fee_liquidity_provenance_case(position_basis_snapshot) != 'basis_only_mints':
            return False
        protocol_fee_liquidity = self._to_decimal(position_basis_snapshot.basis_protocol_fee_liquidity_minted())
        if protocol_fee_liquidity is None or protocol_fee_liquidity <= Decimal('0'):
            return False
        return self._decimal_equal(current_liquidity, tracked_liquidity + protocol_fee_liquidity)

    def _safe_fee_to_continuous_nonzero_prior_add_basis(
        self,
        *,
        position_basis_snapshot: dict,
        current_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        if current_liquidity is None or tracked_liquidity is None:
            return False
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        if position_basis_snapshot.fee_to_continuity_case() != 'continuous_no_changes_after_basis':
            return False
        owner = position_basis_snapshot.fee_to_continuity_owner()
        if owner in (None, ''):
            return False
        if position_basis_snapshot.fee_to_account_at_basis() != owner:
            return False
        if position_basis_snapshot.fee_to_account_latest_known() != owner:
            return False
        protocol_fee_liquidity = self._to_decimal(position_basis_snapshot.fee_to_continuous_protocol_fee_liquidity_current())
        if protocol_fee_liquidity is None or protocol_fee_liquidity <= Decimal('0'):
            return False
        return self._decimal_equal(current_liquidity, tracked_liquidity + protocol_fee_liquidity)

    def _materialized_current_principal_allowed(
        self,
        *,
        position_basis_snapshot,
        pool_has_fee_to: bool,
        owner_receives_protocol_fees: bool,
        current_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        exact_case = self._materialized_exact_current_principal_case(position_basis_snapshot)
        if exact_case is None:
            return False
        if not pool_has_fee_to:
            return True
        if not owner_receives_protocol_fees:
            return True
        if (
            current_liquidity is not None
            and tracked_liquidity is not None
            and current_liquidity <= tracked_liquidity
        ):
            return True
        if self._materialized_post_basis_remove_count(position_basis_snapshot) == 0:
            return (
                self._prior_liquidity_before_basis(position_basis_snapshot) == Decimal('0')
                or self._safe_fee_to_basis_only_nonzero_prior_add_basis(
                    position_basis_snapshot=position_basis_snapshot,
                    current_liquidity=current_liquidity,
                    tracked_liquidity=tracked_liquidity,
                )
                or self._safe_fee_to_continuous_nonzero_prior_add_basis(
                    position_basis_snapshot=position_basis_snapshot,
                    current_liquidity=current_liquidity,
                    tracked_liquidity=tracked_liquidity,
                )
            )
        # Later removes are only exact when the current owner's protocol-fee LP is explicitly isolated.
        # If fee_to changed after basis and protocol-fee mints for non-owner accounts are also present,
        # the snapshot cannot attribute later fee dilution to this position with certainty.
        return self._protocol_fee_split_supported_for_materialized_remove(position_basis_snapshot)

    def _protocol_fee_split_supported_for_materialized_remove(self, position_basis_snapshot: dict) -> bool:
        return True

    def _materialized_protocol_fee_split_case(
        self,
        *,
        position_basis_snapshot,
        owner_receives_protocol_fees: bool,
        current_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> str | None:
        if current_liquidity is None or tracked_liquidity is None or current_liquidity <= tracked_liquidity:
            return None
        if self._safe_all_protocol_fee_mints_owned_by_current_owner(
            position_basis_snapshot=position_basis_snapshot,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'all_protocol_fee_mints_owned_by_current_owner'
        if self._safe_current_owner_protocol_fee_component_proven(
            position_basis_snapshot=position_basis_snapshot,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'current_owner_protocol_fee_component_proven'
        if not owner_receives_protocol_fees:
            return 'owner_not_fee_to'
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        basis_type = str(position_basis_snapshot.basis_type() or '')
        if basis_type == 'remove_liquidity':
            return 'fee_to_latest_remove_basis'
        prior_liquidity_before_basis = self._prior_liquidity_before_basis(position_basis_snapshot)
        if prior_liquidity_before_basis == Decimal('0'):
            return 'fee_to_opening_add_from_zero'
        if self._safe_fee_to_basis_only_nonzero_prior_add_basis(
            position_basis_snapshot=position_basis_snapshot,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'fee_to_basis_only_nonzero_prior_add_basis'
        if self._safe_fee_to_continuous_nonzero_prior_add_basis(
            position_basis_snapshot=position_basis_snapshot,
            current_liquidity=current_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'fee_to_continuous_nonzero_prior_add_basis'
        if self._materialized_post_basis_remove_count(position_basis_snapshot) > 0:
            return 'fee_to_nonzero_prior_add_basis_unresolved'
        if self._materialized_exact_current_principal_case(position_basis_snapshot) is not None:
            return 'fee_to_materialized_nonzero_prior_add_basis'
        return 'fee_to_nonzero_prior_add_basis_unresolved'

    def _unresolved_protocol_fee_profile(
        self,
        *,
        position_basis_snapshot,
        materialized_protocol_fee_split_case: str | None,
    ) -> str | None:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        return self.protocol_fee_split_semantics.unresolved_profile(
            materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
            protocol_fee_current_owner_timing_case=self._current_owner_timing_case(position_basis_snapshot),
            fee_to_continuity_case=position_basis_snapshot.fee_to_continuity_case(),
            protocol_fee_current_owner_provenance_case=self._materialized_current_owner_protocol_fee_provenance_case(
                position_basis_snapshot
            ),
        )

    def _unresolved_protocol_fee_semantic(
        self,
        *,
        position_basis_snapshot: dict,
        materialized_protocol_fee_split_case: str | None,
    ) -> str:
        return self.protocol_fee_split_semantics.unresolved_semantic(
            self._unresolved_protocol_fee_profile(
                position_basis_snapshot=position_basis_snapshot,
                materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
            )
        )

    def _unresolved_protocol_fee_explanation(
        self,
        *,
        position_basis_snapshot: dict,
        materialized_protocol_fee_split_case: str | None,
    ) -> str | None:
        return self.protocol_fee_split_semantics.unresolved_explanation(
            self._unresolved_protocol_fee_semantic(
                position_basis_snapshot=position_basis_snapshot,
                materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
            )
        )

    def _current_owner_timing_case(self, position_basis_snapshot) -> str:
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        basis_owned = self._to_decimal(position_basis_snapshot.basis_protocol_fee_liquidity_owned_by_current_owner()) or Decimal('0')
        post_basis_owned = self._to_decimal(position_basis_snapshot.post_basis_protocol_fee_liquidity_owned_by_current_owner()) or Decimal('0')
        post_basis_owned_before_first_add = self._to_decimal(
            position_basis_snapshot.post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add()
        ) or Decimal('0')
        if basis_owned == 0 and post_basis_owned == 0 and post_basis_owned_before_first_add == 0:
            return 'no_current_owner_protocol_fee'
        if post_basis_owned_before_first_add > post_basis_owned:
            return 'inconsistent_before_first_add_exceeds_post_basis'
        if basis_owned > 0 and post_basis_owned == 0:
            return 'basis_only'
        if basis_owned == 0 and post_basis_owned > 0:
            if post_basis_owned_before_first_add == post_basis_owned:
                return 'post_basis_only_before_first_add_only'
            return 'post_basis_only_with_later_add_present'
        if basis_owned > 0 and post_basis_owned > 0:
            if post_basis_owned_before_first_add == post_basis_owned:
                return 'basis_and_post_basis_before_first_add_only'
            return 'basis_and_post_basis_with_later_add_present'
        return 'unknown_or_partial'

    def _semantic_facts(self, position_basis_snapshot):
        position_basis_snapshot = self._position_basis_snapshot(position_basis_snapshot)
        return position_basis_snapshot.semantic_facts()

    def _position_basis_snapshot(self, snapshot) -> PositionMetricsPositionBasisSnapshot:
        if isinstance(snapshot, PositionMetricsPositionBasisSnapshot):
            return snapshot
        return PositionMetricsPositionBasisSnapshot(snapshot)

    def _pool_state_snapshot(self, snapshot) -> PositionMetricsPoolStateSnapshot:
        if isinstance(snapshot, PositionMetricsPoolStateSnapshot):
            return snapshot
        return PositionMetricsPoolStateSnapshot(snapshot)

    def _semantic_fact(self, position_basis_snapshot, field_name: str) -> object:
        return self._semantic_facts(position_basis_snapshot).get(field_name)

    def _account_payload_to_string(self, account: object) -> str | None:
        return self.account_codec.public_account_from_payload(account)

    def _to_decimal(self, value: object) -> Decimal | None:
        if value is None:
            return None
        return Decimal(str(value))

    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        if value == 0:
            return '0'
        return format(value.quantize(self.display_quantum).normalize(), 'f')

    def _normalize_non_negative(self, value: Decimal) -> Decimal:
        if abs(value) <= self.display_quantum:
            return Decimal('0')
        return value

    def _decimal_equal(self, left: object, right: object) -> bool:
        if left is None or right is None:
            return left is right
        return self._to_decimal(left) == self._to_decimal(right)

    def _int_or_none(self, value: object) -> int | None:
        if value in (None, ''):
            return None
        return int(value)
