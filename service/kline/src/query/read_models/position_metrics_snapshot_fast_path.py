import json
from decimal import Decimal
from query.read_models.position_metrics_protocol_fee_split_semantics import PositionMetricsProtocolFeeSplitSemantics


class PositionMetricsSnapshotFastPath:
    def __init__(
        self,
        *,
        display_quantum: Decimal = Decimal('0.000000000000000001'),
        protocol_fee_split_semantics: PositionMetricsProtocolFeeSplitSemantics | None = None,
    ):
        self.display_quantum = display_quantum
        self.protocol_fee_split_semantics = protocol_fee_split_semantics or PositionMetricsProtocolFeeSplitSemantics()

    def resolve(
        self,
        *,
        position: dict,
        payload: dict,
        position_basis_snapshot: dict | None,
        pool_state_snapshot: dict | None,
    ) -> dict | None:
        if not self._eligible(
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
        owner_is_fee_to = self._account_payload_to_string((data.get('pool') or {}).get('fee_to')) == position['owner']
        pool_has_fee_to = (data.get('pool') or {}).get('fee_to') is not None
        redeemable_amount0 = self._serialize_decimal(self._to_decimal(liquidity.get('amount0')))
        redeemable_amount1 = self._serialize_decimal(self._to_decimal(liquidity.get('amount1')))
        materialized_protocol_fee_split_case = self._materialized_protocol_fee_split_case(
            position_basis_snapshot=position_basis_snapshot,
            owner_is_fee_to=owner_is_fee_to,
            live_liquidity=liquidity_value,
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
            owner_is_fee_to=owner_is_fee_to,
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
        exact_case = self._exact_case(
            position_basis_snapshot=position_basis_snapshot,
            owner_is_fee_to=owner_is_fee_to,
            last_transaction_id=self._int_or_none(pool_state_snapshot.get('last_transaction_id')),
            basis_transaction_id=self._int_or_none(position_basis_snapshot.get('basis_transaction_id')),
            fee_free_basis_transaction_id=self._int_or_none(pool_state_snapshot.get('fee_free_basis_transaction_id')),
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
        live_metrics = {
            'position_liquidity_live': self._serialize_decimal(liquidity_value),
            'total_supply_live': self._serialize_decimal(total_supply_value),
            'exact_share_ratio': share_ratio,
            'redeemable_amount0': redeemable_amount0,
            'redeemable_amount1': redeemable_amount1,
            'virtual_initial_liquidity': bool(data.get('virtualInitialLiquidity')),
            'metrics_status': 'exact_no_swap_history',
            'exact_fee_supported': True,
            'exact_principal_supported': True,
            'owner_is_fee_to': owner_is_fee_to,
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
        return {
            'live_metrics': live_metrics,
            'snapshot_shadow': {
                'owner': position['owner'],
                'pool_application': position['pool_application'],
                'pool_id': position['pool_id'],
                'status': position.get('status') or 'active',
                'metrics_status': live_metrics['metrics_status'],
                'exact_fee_supported': True,
                'exact_principal_supported': True,
                'snapshot_shadow': {
                    'comparable': True,
                    'position_basis_snapshot_present': True,
                    'pool_state_snapshot_present': True,
                    'mismatch_codes': [],
                    'readiness': 'candidate',
                    'readiness_reason_codes': [],
                    'exact_case': exact_case,
                    'live_position_status': position.get('status') or 'active',
                    'live_current_liquidity': position.get('current_liquidity'),
                    'live_metrics_status': live_metrics['metrics_status'],
                    'computation_blockers': [],
                    'value_warning_codes': [],
                    'latest_position_transaction_id': self._int_or_none(position_basis_snapshot.get('basis_transaction_id')),
                    'latest_position_created_at': self._int_or_none(position_basis_snapshot.get('basis_time_ms')),
                    'latest_pool_transaction_id': self._int_or_none(pool_state_snapshot.get('last_transaction_id')),
                    'latest_pool_trade_time_ms': self._int_or_none(pool_state_snapshot.get('last_trade_time_ms')),
                    'latest_pool_liquidity_event_time_ms': self._int_or_none(
                        pool_state_snapshot.get('last_liquidity_event_time_ms')
                    ),
                    'position_basis_snapshot': {
                        'status': position_basis_snapshot.get('status'),
                        'basis_type': position_basis_snapshot.get('basis_type'),
                        'current_liquidity': position_basis_snapshot.get('current_liquidity'),
                        'basis_transaction_id': self._int_or_none(position_basis_snapshot.get('basis_transaction_id')),
                        'basis_time_ms': self._int_or_none(position_basis_snapshot.get('basis_time_ms')),
                        'basis_opens_current_round': self._basis_opens_current_round(position_basis_snapshot),
                        'has_only_zero_liquidity_before_basis': self._has_only_zero_liquidity_before_basis(
                            position_basis_snapshot
                        ),
                        'current_round_liquidity_event_count': self._current_round_liquidity_event_count(
                            position_basis_snapshot
                        ),
                        'current_round_started_at': self._current_round_started_at(position_basis_snapshot),
                        'current_round_started_transaction_id': self._current_round_started_transaction_id(
                            position_basis_snapshot
                        ),
                        'current_round_trade_count_before_basis': self._current_round_trade_count_before_basis(
                            position_basis_snapshot
                        ),
                        'trade_count_between_basis_and_fee_free_basis': (
                            self._trade_count_between_basis_and_fee_free_basis(position_basis_snapshot)
                        ),
                        'exact_current_principal_case': self._materialized_exact_current_principal_case(
                            position_basis_snapshot
                        ),
                        'protocol_fee_liquidity_provenance_case': (
                            self._materialized_protocol_fee_liquidity_provenance_case(position_basis_snapshot)
                        ),
                        'basis_protocol_fee_liquidity_minted': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'basis_protocol_fee_liquidity_minted',
                            )
                        ),
                        'post_basis_protocol_fee_liquidity_minted': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'post_basis_protocol_fee_liquidity_minted',
                            )
                        ),
                        'post_basis_protocol_fee_mint_event_count': (
                            self._materialized_protocol_fee_mint_event_count(position_basis_snapshot)
                        ),
                        'post_basis_protocol_fee_liquidity_minted_before_first_add': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'post_basis_protocol_fee_liquidity_minted_before_first_add',
                            )
                        ),
                        'fee_to_continuous_protocol_fee_liquidity_current': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'fee_to_continuous_protocol_fee_liquidity_current',
                            )
                        ),
                        'protocol_fee_current_owner_provenance_case': (
                            self._materialized_current_owner_protocol_fee_provenance_case(
                                position_basis_snapshot
                            )
                        ),
                        'basis_protocol_fee_liquidity_owned_by_current_owner': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'basis_protocol_fee_liquidity_owned_by_current_owner',
                            )
                        ),
                        'post_basis_protocol_fee_liquidity_owned_by_current_owner': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'post_basis_protocol_fee_liquidity_owned_by_current_owner',
                            )
                        ),
                        'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add',
                            )
                        ),
                        'protocol_fee_liquidity_owned_by_current_owner_current': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'protocol_fee_liquidity_owned_by_current_owner_current',
                            )
                        ),
                        'protocol_fee_liquidity_owned_by_other_accounts': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'protocol_fee_liquidity_owned_by_other_accounts',
                            )
                        ),
                        'protocol_fee_liquidity_owner_unknown': (
                            self._materialized_protocol_fee_liquidity_value(
                                position_basis_snapshot,
                                'protocol_fee_liquidity_owner_unknown',
                            )
                        ),
                        'fee_to_continuity_case': self._fee_to_continuity_field(
                            position_basis_snapshot,
                            'continuity_case',
                        ),
                        'fee_to_continuity_change_count_after_basis': self._fee_to_continuity_int_field(
                            position_basis_snapshot,
                            'change_count_after_basis',
                        ),
                        'fee_to_continuity_known_before_basis': self._fee_to_continuity_bool_field(
                            position_basis_snapshot,
                            'known_before_basis',
                        ),
                        'fee_to_account_at_basis': self._fee_to_continuity_field(
                            position_basis_snapshot,
                            'fee_to_account_at_basis',
                        ),
                        'fee_to_account_latest_known': self._fee_to_continuity_field(
                            position_basis_snapshot,
                            'fee_to_account_latest_known',
                        ),
                        'materialized_protocol_fee_split_case': materialized_protocol_fee_split_case,
                        'protocol_fee_split_semantic': self.protocol_fee_split_semantics.semantic_for_case(
                            materialized_protocol_fee_split_case
                        ),
                        'unresolved_protocol_fee_profile': self._unresolved_protocol_fee_profile(
                            position_basis_snapshot=position_basis_snapshot,
                            materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
                        ),
                        'unresolved_protocol_fee_semantic': self._unresolved_protocol_fee_semantic(
                            position_basis_snapshot=position_basis_snapshot,
                            materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
                        ),
                        'unresolved_protocol_fee_explanation': self._unresolved_protocol_fee_explanation(
                            position_basis_snapshot=position_basis_snapshot,
                            materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
                        ),
                    },
                    'pool_state_snapshot': {
                        'last_transaction_id': self._int_or_none(pool_state_snapshot.get('last_transaction_id')),
                        'last_trade_time_ms': self._int_or_none(pool_state_snapshot.get('last_trade_time_ms')),
                        'last_liquidity_event_time_ms': self._int_or_none(
                            pool_state_snapshot.get('last_liquidity_event_time_ms')
                        ),
                    },
                },
            },
        }

    def _eligible(
        self,
        *,
        position: dict,
        payload: dict,
        position_basis_snapshot: dict | None,
        pool_state_snapshot: dict | None,
    ) -> bool:
        if position_basis_snapshot is None or pool_state_snapshot is None:
            return False
        if str(position.get('status') or 'active') != 'active':
            return False
        if str(position_basis_snapshot.get('status') or '') != 'active':
            return False
        basis_type = str(position_basis_snapshot.get('basis_type') or '')
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
        live_liquidity = self._to_decimal(liquidity.get('liquidity'))
        if live_liquidity is None:
            return False
        if self._to_decimal((payload.get('data') or {}).get('totalSupply')) is None:
            return False
        if self._to_decimal(liquidity.get('amount0')) is None or self._to_decimal(liquidity.get('amount1')) is None:
            return False
        if not self._decimal_equal(position.get('current_liquidity'), position_basis_snapshot.get('current_liquidity')):
            return False
        tracked_liquidity = self._tracked_liquidity_value(position_basis_snapshot)
        if tracked_liquidity is None:
            return False
        live_liquidity_allowed = self._decimal_equal(position.get('current_liquidity'), liquidity.get('liquidity'))
        if (
            not live_liquidity_allowed
            and not self._eligible_fee_to_opening_mint_case(
                position=position,
                payload=payload,
                position_basis_snapshot=position_basis_snapshot,
                tracked_liquidity=tracked_liquidity,
                live_liquidity=live_liquidity,
            )
            and not self._safe_current_owner_protocol_fee_component_proven(
                position_basis_snapshot=position_basis_snapshot,
                live_liquidity=live_liquidity,
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
        opened_at = self._int_or_none(position.get('opened_at'))
        basis_time_ms = self._int_or_none(position_basis_snapshot.get('basis_time_ms'))
        if opened_at == basis_time_ms:
            return True
        if self._materialized_exact_current_principal_case(position_basis_snapshot) is not None:
            return True
        if opened_at is None or basis_time_ms is None or opened_at > basis_time_ms:
            return False
        return (
            self._basis_opens_current_round(position_basis_snapshot)
            or self._current_round_trade_count_before_basis(position_basis_snapshot) == 0
        )

    def _fee_free_basis_compatible(
        self,
        *,
        position_basis_snapshot: dict,
        pool_state_snapshot: dict,
    ) -> bool:
        basis_transaction_id = self._int_or_none(position_basis_snapshot.get('basis_transaction_id'))
        basis_time_ms = self._int_or_none(position_basis_snapshot.get('basis_time_ms'))
        fee_free_basis_transaction_id = self._int_or_none(pool_state_snapshot.get('fee_free_basis_transaction_id'))
        fee_free_basis_time_ms = self._int_or_none(pool_state_snapshot.get('fee_free_basis_time_ms'))
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
        if self._materialized_exact_current_principal_case(position_basis_snapshot) is not None:
            return True
        return self._trade_count_between_basis_and_fee_free_basis(position_basis_snapshot) == 0

    def _principal_and_fee(
        self,
        *,
        liquidity_value: Decimal | None,
        tracked_liquidity_value: Decimal | None,
        total_supply_value: Decimal | None,
        redeemable_amount0: Decimal | None,
        redeemable_amount1: Decimal | None,
        position_basis_snapshot: dict,
        pool_state_snapshot: dict,
        owner_is_fee_to: bool,
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
            owner_is_fee_to=owner_is_fee_to,
            position_basis_snapshot=position_basis_snapshot,
            live_liquidity=liquidity_value,
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
            owner_is_fee_to=owner_is_fee_to,
            live_liquidity=liquidity_value,
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
        last_transaction_id = self._int_or_none(pool_state_snapshot.get('last_transaction_id'))
        basis_transaction_id = self._int_or_none(position_basis_snapshot.get('basis_transaction_id'))
        if last_transaction_id == basis_transaction_id:
            return (
                self._normalize_non_negative(redeemable_amount0 - protocol_fee_amount0),
                self._normalize_non_negative(redeemable_amount1 - protocol_fee_amount1),
                Decimal('0'),
                Decimal('0'),
                protocol_fee_amount0,
                protocol_fee_amount1,
            )
        fee_free_reserve_0 = self._to_decimal(pool_state_snapshot.get('fee_free_reserve_0'))
        fee_free_reserve_1 = self._to_decimal(pool_state_snapshot.get('fee_free_reserve_1'))
        if fee_free_reserve_0 is None or fee_free_reserve_1 is None:
            return None, None, None, None, None, None
        principal_amount0 = self._normalize_non_negative(liquidity_basis * fee_free_reserve_0 / total_supply_value)
        principal_amount1 = self._normalize_non_negative(liquidity_basis * fee_free_reserve_1 / total_supply_value)
        fee_amount0 = self._normalize_non_negative(redeemable_amount0 - protocol_fee_amount0 - principal_amount0)
        fee_amount1 = self._normalize_non_negative(redeemable_amount1 - protocol_fee_amount1 - principal_amount1)
        if fee_amount0 < 0 or fee_amount1 < 0:
            return None, None, None, None, None, None
        return principal_amount0, principal_amount1, fee_amount0, fee_amount1, protocol_fee_amount0, protocol_fee_amount1

    def _exact_case(
        self,
        *,
        position_basis_snapshot: dict,
        owner_is_fee_to: bool,
        last_transaction_id: int | None,
        basis_transaction_id: int | None,
        fee_free_basis_transaction_id: int | None,
        liquidity_value: Decimal | None,
        tracked_liquidity_value: Decimal | None,
    ) -> str:
        fee_to_opening_mint = (
            owner_is_fee_to
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
        if fee_to_opening_mint and post_basis_liquidity_changes:
            if self._materialized_exact_current_principal_case(position_basis_snapshot) is not None:
                return self._materialized_exact_current_principal_case(position_basis_snapshot).replace(
                    'post_basis_liquidity_changes_with_intervening_swaps',
                    'fee_to_opening_mint_post_basis_liquidity_changes_with_intervening_swaps',
                ).replace(
                    'post_basis_liquidity_changes_without_intervening_swaps',
                    'fee_to_opening_mint_post_basis_liquidity_changes_without_intervening_swaps',
                )
            return 'fee_to_opening_mint_post_basis_liquidity_changes'
        if self._materialized_exact_current_principal_case(position_basis_snapshot) is not None:
            return self._materialized_exact_current_principal_case(position_basis_snapshot)
        if post_basis_liquidity_changes:
            return 'post_basis_liquidity_changes'
        if fee_to_opening_mint and no_post_basis_transactions:
            return 'fee_to_opening_mint_no_post_basis_transactions'
        if fee_to_opening_mint:
            return 'fee_to_opening_mint_post_basis_swaps'
        if no_post_basis_transactions:
            return 'no_post_basis_transactions'
        return 'post_basis_swaps'

    def _eligible_fee_to_opening_mint_case(
        self,
        *,
        position: dict,
        payload: dict,
        position_basis_snapshot: dict,
        tracked_liquidity: Decimal,
        live_liquidity: Decimal | None,
    ) -> bool:
        if live_liquidity is None or live_liquidity <= tracked_liquidity:
            return False
        if self._account_payload_to_string(((payload.get('data') or {}).get('pool') or {}).get('fee_to')) != position['owner']:
            return False
        if self._materialized_exact_current_principal_case(position_basis_snapshot) is not None:
            return True
        if str(position_basis_snapshot.get('basis_type') or '') != 'add_liquidity':
            return False
        if self._prior_liquidity_before_basis(position_basis_snapshot) != Decimal('0'):
            return False
        return True

    def _protocol_fee_split(
        self,
        *,
        owner_is_fee_to: bool,
        position_basis_snapshot: dict,
        live_liquidity: Decimal,
        tracked_liquidity: Decimal,
        redeemable_amount0: Decimal,
        redeemable_amount1: Decimal,
    ) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
        if live_liquidity <= tracked_liquidity:
            return Decimal('0'), Decimal('0'), tracked_liquidity
        if self._safe_current_owner_protocol_fee_component_proven(
            position_basis_snapshot=position_basis_snapshot,
            live_liquidity=live_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            protocol_fee_liquidity = self._materialized_protocol_fee_liquidity_decimal(
                position_basis_snapshot,
                'protocol_fee_liquidity_owned_by_current_owner_current',
            )
            if protocol_fee_liquidity is None:
                return None, None, None
            protocol_fee_ratio = protocol_fee_liquidity / live_liquidity
            protocol_fee_amount0 = self._normalize_non_negative(redeemable_amount0 * protocol_fee_ratio)
            protocol_fee_amount1 = self._normalize_non_negative(redeemable_amount1 * protocol_fee_ratio)
            return protocol_fee_amount0, protocol_fee_amount1, tracked_liquidity
        if not owner_is_fee_to:
            return None, None, None
        materialized_protocol_fee_split_case = self._materialized_protocol_fee_split_case(
            position_basis_snapshot=position_basis_snapshot,
            owner_is_fee_to=owner_is_fee_to,
            live_liquidity=live_liquidity,
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
                live_liquidity=live_liquidity,
                tracked_liquidity=tracked_liquidity,
            )
            if protocol_fee_liquidity is None:
                return None, None, None
            protocol_fee_ratio = protocol_fee_liquidity / live_liquidity
            protocol_fee_amount0 = self._normalize_non_negative(redeemable_amount0 * protocol_fee_ratio)
            protocol_fee_amount1 = self._normalize_non_negative(redeemable_amount1 * protocol_fee_ratio)
            return protocol_fee_amount0, protocol_fee_amount1, tracked_liquidity
        if str(position_basis_snapshot.get('basis_type') or '') != 'add_liquidity':
            return None, None, None
        if self._prior_liquidity_before_basis(position_basis_snapshot) != Decimal('0'):
            return None, None, None
        protocol_fee_ratio = (live_liquidity - tracked_liquidity) / live_liquidity
        protocol_fee_amount0 = self._normalize_non_negative(redeemable_amount0 * protocol_fee_ratio)
        protocol_fee_amount1 = self._normalize_non_negative(redeemable_amount1 * protocol_fee_ratio)
        return protocol_fee_amount0, protocol_fee_amount1, tracked_liquidity

    def _tracked_liquidity_value(self, position_basis_snapshot: dict) -> Decimal | None:
        return self._to_decimal(position_basis_snapshot.get('current_liquidity'))

    def _prior_liquidity_before_basis(self, position_basis_snapshot: dict) -> Decimal:
        payload = position_basis_snapshot.get('state_payload_json')
        payload_dict = self._payload_dict(payload)
        return self._to_decimal(payload_dict.get('prior_liquidity_before_basis')) or Decimal('0')

    def _has_only_zero_liquidity_before_basis(self, position_basis_snapshot: dict) -> bool:
        payload = position_basis_snapshot.get('state_payload_json')
        payload_dict = self._payload_dict(payload)
        return bool(payload_dict.get('has_only_zero_liquidity_before_basis'))

    def _basis_opens_current_round(self, position_basis_snapshot: dict) -> bool:
        payload = position_basis_snapshot.get('state_payload_json')
        payload_dict = self._payload_dict(payload)
        return bool(payload_dict.get('basis_opens_current_round'))

    def _current_round_liquidity_event_count(self, position_basis_snapshot: dict) -> int | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        value = payload.get('current_round_liquidity_event_count')
        if value in (None, ''):
            return None
        return int(value)

    def _current_round_started_at(self, position_basis_snapshot: dict) -> int | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        value = payload.get('current_round_started_at')
        if value in (None, ''):
            return None
        return int(value)

    def _current_round_started_transaction_id(self, position_basis_snapshot: dict) -> int | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        value = payload.get('current_round_started_transaction_id')
        if value in (None, ''):
            return None
        return int(value)

    def _current_round_trade_count_before_basis(self, position_basis_snapshot: dict) -> int | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        value = payload.get('current_round_trade_count_before_basis')
        if value in (None, ''):
            return None
        return int(value)

    def _trade_count_between_basis_and_fee_free_basis(self, position_basis_snapshot: dict) -> int | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        value = payload.get('trade_count_between_basis_and_fee_free_basis')
        if value in (None, ''):
            return None
        return int(value)

    def _materialized_principal_amount_current(
        self,
        position_basis_snapshot: dict,
        field_name: str,
    ) -> Decimal | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return None
        value = exact_current_principal.get(field_name)
        if value in (None, ''):
            return None
        return self._to_decimal(value)

    def _materialized_exact_current_principal_case(self, position_basis_snapshot: dict) -> str | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return None
        value = exact_current_principal.get('exact_current_principal_case')
        if value in (None, ''):
            return None
        return str(value)

    def _materialized_post_basis_remove_count(self, position_basis_snapshot: dict) -> int:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return 0
        value = exact_current_principal.get('post_basis_remove_count')
        if value in (None, ''):
            return 0
        return int(value)

    def _materialized_protocol_fee_liquidity_value(
        self,
        position_basis_snapshot: dict,
        field_name: str,
    ) -> str | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return None
        value = exact_current_principal.get(field_name)
        if value in (None, ''):
            return None
        return str(value)

    def _materialized_protocol_fee_mint_event_count(self, position_basis_snapshot: dict) -> int | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return None
        value = exact_current_principal.get('post_basis_protocol_fee_mint_event_count')
        if value in (None, ''):
            return None
        return int(value)

    def _materialized_protocol_fee_liquidity_provenance_case(self, position_basis_snapshot: dict) -> str | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return None
        value = exact_current_principal.get('protocol_fee_liquidity_provenance_case')
        if value in (None, ''):
            return None
        return str(value)

    def _materialized_current_owner_protocol_fee_provenance_case(self, position_basis_snapshot: dict) -> str | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return None
        value = exact_current_principal.get('protocol_fee_current_owner_provenance_case')
        if value in (None, ''):
            return None
        return str(value)

    def _materialized_protocol_fee_liquidity_decimal(
        self,
        position_basis_snapshot: dict,
        field_name: str,
    ) -> Decimal | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        exact_current_principal = payload.get('exact_current_principal')
        if not isinstance(exact_current_principal, dict):
            return None
        value = exact_current_principal.get(field_name)
        if value in (None, ''):
            return None
        return self._to_decimal(value)

    def _fee_to_continuity_field(
        self,
        position_basis_snapshot: dict,
        field_name: str,
    ) -> str | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        continuity = payload.get('fee_to_continuity')
        if not isinstance(continuity, dict):
            return None
        value = continuity.get(field_name)
        if value in (None, ''):
            return None
        return str(value)

    def _fee_to_continuity_int_field(
        self,
        position_basis_snapshot: dict,
        field_name: str,
    ) -> int | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        continuity = payload.get('fee_to_continuity')
        if not isinstance(continuity, dict):
            return None
        value = continuity.get(field_name)
        if value in (None, ''):
            return None
        return int(value)

    def _fee_to_continuity_bool_field(
        self,
        position_basis_snapshot: dict,
        field_name: str,
    ) -> bool | None:
        payload = self._payload_dict(position_basis_snapshot.get('state_payload_json'))
        continuity = payload.get('fee_to_continuity')
        if not isinstance(continuity, dict):
            return None
        if field_name not in continuity:
            return None
        return bool(continuity.get(field_name))

    def _fee_to_continuity_owner(self, position_basis_snapshot: dict) -> str | None:
        return self._fee_to_continuity_field(position_basis_snapshot, 'owner')

    def _protocol_fee_liquidity_current(
        self,
        *,
        position_basis_snapshot: dict,
        live_liquidity: Decimal,
        tracked_liquidity: Decimal,
    ) -> Decimal | None:
        materialized_protocol_fee_split_case = self._materialized_protocol_fee_split_case(
            position_basis_snapshot=position_basis_snapshot,
            owner_is_fee_to=True,
            live_liquidity=live_liquidity,
            tracked_liquidity=tracked_liquidity,
        )
        if materialized_protocol_fee_split_case == 'fee_to_continuous_nonzero_prior_add_basis':
            return self._materialized_protocol_fee_liquidity_decimal(
                position_basis_snapshot,
                'fee_to_continuous_protocol_fee_liquidity_current',
            )
        if materialized_protocol_fee_split_case == 'fee_to_basis_only_nonzero_prior_add_basis':
            return self._materialized_protocol_fee_liquidity_decimal(
                position_basis_snapshot,
                'basis_protocol_fee_liquidity_minted',
            )
        if materialized_protocol_fee_split_case in {
            'all_protocol_fee_mints_owned_by_current_owner',
            'current_owner_protocol_fee_component_proven',
        }:
            return self._materialized_protocol_fee_liquidity_decimal(
                position_basis_snapshot,
                'protocol_fee_liquidity_owned_by_current_owner_current',
            )
        return live_liquidity - tracked_liquidity

    def _safe_all_protocol_fee_mints_owned_by_current_owner(
        self,
        *,
        position_basis_snapshot: dict,
        live_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        if live_liquidity is None or tracked_liquidity is None:
            return False
        if self._materialized_current_owner_protocol_fee_provenance_case(position_basis_snapshot) != (
            'all_mints_owned_by_current_owner'
        ):
            return False
        owned_by_current_owner = self._materialized_protocol_fee_liquidity_decimal(
            position_basis_snapshot,
            'protocol_fee_liquidity_owned_by_current_owner_current',
        )
        owned_by_other_accounts = self._materialized_protocol_fee_liquidity_decimal(
            position_basis_snapshot,
            'protocol_fee_liquidity_owned_by_other_accounts',
        )
        owner_unknown = self._materialized_protocol_fee_liquidity_decimal(
            position_basis_snapshot,
            'protocol_fee_liquidity_owner_unknown',
        )
        if owned_by_current_owner is None or owned_by_current_owner <= Decimal('0'):
            return False
        if owned_by_other_accounts not in (None, Decimal('0')):
            return False
        if owner_unknown not in (None, Decimal('0')):
            return False
        return self._decimal_equal(live_liquidity, tracked_liquidity + owned_by_current_owner)

    def _safe_current_owner_protocol_fee_component_proven(
        self,
        *,
        position_basis_snapshot: dict,
        live_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        if live_liquidity is None or tracked_liquidity is None:
            return False
        owned_by_current_owner = self._materialized_protocol_fee_liquidity_decimal(
            position_basis_snapshot,
            'protocol_fee_liquidity_owned_by_current_owner_current',
        )
        if owned_by_current_owner is None or owned_by_current_owner <= Decimal('0'):
            return False
        return self._decimal_equal(live_liquidity, tracked_liquidity + owned_by_current_owner)

    def _safe_fee_to_basis_only_nonzero_prior_add_basis(
        self,
        *,
        position_basis_snapshot: dict,
        live_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        if live_liquidity is None or tracked_liquidity is None:
            return False
        if self._fee_to_continuity_bool_field(position_basis_snapshot, 'known_before_basis') is not True:
            return False
        owner = self._fee_to_continuity_owner(position_basis_snapshot)
        if owner in (None, ''):
            return False
        if self._fee_to_continuity_field(position_basis_snapshot, 'fee_to_account_at_basis') != owner:
            return False
        if self._materialized_protocol_fee_liquidity_provenance_case(position_basis_snapshot) != 'basis_only_mints':
            return False
        protocol_fee_liquidity = self._materialized_protocol_fee_liquidity_decimal(
            position_basis_snapshot,
            'basis_protocol_fee_liquidity_minted',
        )
        if protocol_fee_liquidity is None or protocol_fee_liquidity <= Decimal('0'):
            return False
        return self._decimal_equal(live_liquidity, tracked_liquidity + protocol_fee_liquidity)

    def _safe_fee_to_continuous_nonzero_prior_add_basis(
        self,
        *,
        position_basis_snapshot: dict,
        live_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        if live_liquidity is None or tracked_liquidity is None:
            return False
        if self._fee_to_continuity_field(position_basis_snapshot, 'continuity_case') != 'continuous_no_changes_after_basis':
            return False
        owner = self._fee_to_continuity_owner(position_basis_snapshot)
        if owner in (None, ''):
            return False
        if self._fee_to_continuity_field(position_basis_snapshot, 'fee_to_account_at_basis') != owner:
            return False
        if self._fee_to_continuity_field(position_basis_snapshot, 'fee_to_account_latest_known') != owner:
            return False
        protocol_fee_liquidity = self._materialized_protocol_fee_liquidity_decimal(
            position_basis_snapshot,
            'fee_to_continuous_protocol_fee_liquidity_current',
        )
        if protocol_fee_liquidity is None or protocol_fee_liquidity <= Decimal('0'):
            return False
        return self._decimal_equal(live_liquidity, tracked_liquidity + protocol_fee_liquidity)

    def _materialized_current_principal_allowed(
        self,
        *,
        position_basis_snapshot: dict,
        pool_has_fee_to: bool,
        owner_is_fee_to: bool,
        live_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> bool:
        exact_case = self._materialized_exact_current_principal_case(position_basis_snapshot)
        if exact_case is None:
            return False
        if not pool_has_fee_to:
            return True
        if not owner_is_fee_to:
            return True
        if (
            live_liquidity is not None
            and tracked_liquidity is not None
            and live_liquidity <= tracked_liquidity
        ):
            return True
        if self._materialized_post_basis_remove_count(position_basis_snapshot) == 0:
            return (
                self._prior_liquidity_before_basis(position_basis_snapshot) == Decimal('0')
                or self._safe_fee_to_basis_only_nonzero_prior_add_basis(
                    position_basis_snapshot=position_basis_snapshot,
                    live_liquidity=live_liquidity,
                    tracked_liquidity=tracked_liquidity,
                )
                or self._safe_fee_to_continuous_nonzero_prior_add_basis(
                    position_basis_snapshot=position_basis_snapshot,
                    live_liquidity=live_liquidity,
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
        position_basis_snapshot: dict,
        owner_is_fee_to: bool,
        live_liquidity: Decimal | None,
        tracked_liquidity: Decimal | None,
    ) -> str | None:
        if live_liquidity is None or tracked_liquidity is None or live_liquidity <= tracked_liquidity:
            return None
        if self._safe_all_protocol_fee_mints_owned_by_current_owner(
            position_basis_snapshot=position_basis_snapshot,
            live_liquidity=live_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'all_protocol_fee_mints_owned_by_current_owner'
        if self._safe_current_owner_protocol_fee_component_proven(
            position_basis_snapshot=position_basis_snapshot,
            live_liquidity=live_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'current_owner_protocol_fee_component_proven'
        if not owner_is_fee_to:
            return 'owner_not_fee_to'
        basis_type = str(position_basis_snapshot.get('basis_type') or '')
        if basis_type == 'remove_liquidity':
            return 'fee_to_latest_remove_basis'
        prior_liquidity_before_basis = self._prior_liquidity_before_basis(position_basis_snapshot)
        if prior_liquidity_before_basis == Decimal('0'):
            return 'fee_to_opening_add_from_zero'
        if self._safe_fee_to_basis_only_nonzero_prior_add_basis(
            position_basis_snapshot=position_basis_snapshot,
            live_liquidity=live_liquidity,
            tracked_liquidity=tracked_liquidity,
        ):
            return 'fee_to_basis_only_nonzero_prior_add_basis'
        if self._safe_fee_to_continuous_nonzero_prior_add_basis(
            position_basis_snapshot=position_basis_snapshot,
            live_liquidity=live_liquidity,
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
        position_basis_snapshot: dict,
        materialized_protocol_fee_split_case: str | None,
    ) -> str | None:
        return self.protocol_fee_split_semantics.unresolved_profile(
            materialized_protocol_fee_split_case=materialized_protocol_fee_split_case,
            protocol_fee_current_owner_timing_case=self._current_owner_timing_case(position_basis_snapshot),
            fee_to_continuity_case=self._fee_to_continuity_field(position_basis_snapshot, 'continuity_case'),
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

    def _current_owner_timing_case(self, position_basis_snapshot: dict) -> str:
        basis_owned = self._materialized_protocol_fee_liquidity_decimal(
            position_basis_snapshot,
            'basis_protocol_fee_liquidity_owned_by_current_owner',
        ) or Decimal('0')
        post_basis_owned = self._materialized_protocol_fee_liquidity_decimal(
            position_basis_snapshot,
            'post_basis_protocol_fee_liquidity_owned_by_current_owner',
        ) or Decimal('0')
        post_basis_owned_before_first_add = self._materialized_protocol_fee_liquidity_decimal(
            position_basis_snapshot,
            'post_basis_protocol_fee_liquidity_owned_by_current_owner_before_first_add',
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

    def _payload_dict(self, payload: object) -> dict:
        if isinstance(payload, dict):
            return payload
        if isinstance(payload, str):
            try:
                parsed = json.loads(payload)
            except Exception:
                return {}
            if isinstance(parsed, dict):
                return parsed
        return {}

    def _account_payload_to_string(self, account: object) -> str | None:
        if not isinstance(account, dict):
            return None
        chain_id = account.get('chain_id')
        owner = account.get('owner')
        if chain_id is None or owner is None:
            return None
        return f'{chain_id}:{owner}'

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
