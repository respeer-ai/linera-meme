from decimal import Decimal

from market.position_metrics_protocol_fee_ownership_tracker import PositionMetricsProtocolFeeOwnershipTracker
from market.position_metrics_snapshot_principal_simulator import PositionMetricsSnapshotPrincipalSimulator
from position_metrics_pool_history_reconstructor import PositionMetricsPoolHistoryReconstructor
from position_metrics_swap_math_support import PositionMetricsSwapMathSupport
from position_metrics_value_support import PositionMetricsValueSupport


class PositionMetricsSnapshotBuilder:
    def __init__(
        self,
        *,
        snapshot_source_repository,
        attos_scale: int = 10 ** 18,
        swap_fee_numerator: int = 997,
        swap_fee_denominator: int = 1000,
        display_quantum: Decimal = Decimal('0.000000000000000001'),
        epsilon: Decimal = Decimal('0.000000000001'),
        liquidity_mint_tolerance_attos: int = 100,
        swap_out_tolerance_attos: int = 1,
    ):
        self.snapshot_source_repository = snapshot_source_repository
        self.value_support = PositionMetricsValueSupport(
            attos_scale=attos_scale,
            display_quantum=display_quantum,
            epsilon=epsilon,
            liquidity_mint_tolerance_attos=liquidity_mint_tolerance_attos,
            swap_out_tolerance_attos=swap_out_tolerance_attos,
        )
        self.swap_math_support = PositionMetricsSwapMathSupport(
            to_attos=self.value_support.to_attos,
            from_attos=self.value_support.from_attos,
            swap_fee_numerator=swap_fee_numerator,
            swap_fee_denominator=swap_fee_denominator,
            swap_out_tolerance_attos=swap_out_tolerance_attos,
        )
        self.principal_simulator = PositionMetricsSnapshotPrincipalSimulator(
            to_attos=self.value_support.to_attos,
            from_attos=self.value_support.from_attos,
            serialize_attos=self._serialize_attos,
            swap_expected_out_attos=self._fee_free_swap_expected_out_attos,
            effective_total_supply_attos=self._effective_total_supply_attos,
        )
        self.protocol_fee_ownership_tracker = PositionMetricsProtocolFeeOwnershipTracker(
            serialize_attos=self._serialize_attos,
        )

    def build_materialization_plan(
        self,
        outputs: list[dict[str, object]],
    ) -> dict[str, object]:
        affected_pools = self._collect_affected_pools(outputs)
        affected_positions = self._collect_affected_positions(outputs)
        pool_states = []
        position_replacements = []

        for pool_application_id, pool_chain_id in affected_pools:
            pool_state = self._build_pool_state(
                pool_application_id=pool_application_id,
                pool_chain_id=pool_chain_id,
            )
            if pool_state is not None:
                pool_states.append(pool_state)

        for owner, pool_application_id, pool_chain_id in affected_positions:
            position_state = self._build_position_state(
                owner=owner,
                pool_application_id=pool_application_id,
                pool_chain_id=pool_chain_id,
            )
            position_replacements.append(
                {
                    'owner': owner,
                    'pool_application_id': pool_application_id,
                    'states': [] if position_state is None else [position_state],
                }
            )

        return {
            'pool_states': pool_states,
            'position_replacements': position_replacements,
            'affected_pool_count': len(affected_pools),
            'affected_position_count': len(affected_positions),
        }

    def _build_pool_state(
        self,
        *,
        pool_application_id: str,
        pool_chain_id: str | None,
    ) -> dict[str, object] | None:
        history = self._load_pool_transaction_history(pool_application_id=pool_application_id)
        if not history:
            return None
        virtual_initial_liquidity = self._infer_virtual_initial_liquidity(history)
        effective_history, states, blockers = self._reconstructor().reconstruct(
            history,
            virtual_initial_liquidity=virtual_initial_liquidity,
        )
        if blockers or not states:
            return None
        latest_state = states[-1]
        live_total_supply_attos = self._effective_total_supply_attos(latest_state)
        fee_free_state, fee_free_basis = self._fee_free_state_from_latest_liquidity_event(
            states=states,
            effective_history=effective_history or [],
        )
        last_trade_time_ms = max(
            (
                int(row.get('created_at') or 0)
                for row in effective_history
                if row.get('transaction_type') in {'BuyToken0', 'SellToken0'}
            ),
            default=None,
        )
        last_liquidity_event_time_ms = max(
            (
                int(row.get('created_at') or 0)
                for row in effective_history
                if row.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}
            ),
            default=None,
        )
        transaction_ids = [
            int(row['transaction_id'])
            for row in effective_history
            if row.get('transaction_id') is not None
        ]
        last_transaction_id = max(transaction_ids) if transaction_ids else None
        swap_count = sum(
            1
            for row in history
            if row.get('transaction_type') in {'BuyToken0', 'SellToken0'}
        )
        return {
            'pool_state_id': pool_application_id,
            'pool_application_id': pool_application_id,
            'pool_chain_id': pool_chain_id or self._parse_pool_chain_id(pool_application_id),
            'last_trade_time_ms': last_trade_time_ms,
            'last_liquidity_event_time_ms': last_liquidity_event_time_ms,
            'last_transaction_id': last_transaction_id,
            'swap_count': swap_count,
            'live_reserve_0': self._serialize_attos(latest_state['reserve0_after']),
            'live_reserve_1': self._serialize_attos(latest_state['reserve1_after']),
            'live_total_supply': self._serialize_attos(live_total_supply_attos),
            'live_k_last': self._serialize_attos(latest_state['k_last_after']),
            'fee_free_basis_transaction_id': fee_free_basis.get('transaction_id') if fee_free_basis is not None else None,
            'fee_free_basis_time_ms': fee_free_basis.get('created_at') if fee_free_basis is not None else None,
            'fee_free_reserve_0': self._serialize_attos(fee_free_state['reserve0']),
            'fee_free_reserve_1': self._serialize_attos(fee_free_state['reserve1']),
            'fee_free_total_supply': self._serialize_attos(
                fee_free_basis['total_supply_after'] if fee_free_basis is not None else latest_state['total_supply_after']
            ),
            'source_event_key': self._pool_source_event_key(
                pool_application_id=pool_application_id,
                last_transaction_id=last_transaction_id,
                last_trade_time_ms=last_trade_time_ms,
                last_liquidity_event_time_ms=last_liquidity_event_time_ms,
            ),
            'state_payload_json': {
                'virtual_initial_liquidity': virtual_initial_liquidity,
                'history_size': len(history),
                'effective_history_size': len(effective_history),
                'last_state': latest_state,
                'fee_free_basis': fee_free_basis,
                'fee_free_state': fee_free_state,
            },
        }

    def _build_position_state(
        self,
        *,
        owner: str,
        pool_application_id: str,
        pool_chain_id: str | None,
    ) -> dict[str, object] | None:
        history = self.snapshot_source_repository.list_position_liquidity_history(
            owner=owner,
            pool_application_id=pool_application_id,
        )
        if not history:
            return None
        pool_trade_history = self.snapshot_source_repository.list_pool_trade_history(
            pool_application_id=pool_application_id,
        )
        pool_liquidity_history = self.snapshot_source_repository.list_pool_liquidity_history(
            pool_application_id=pool_application_id,
        )
        pool_transaction_history = self._load_pool_transaction_history(
            pool_application_id=pool_application_id,
        )
        latest_transaction = history[-1]
        latest_pool_liquidity_transaction = self._latest_row(pool_liquidity_history)
        running_liquidity = 0
        added_liquidity = 0
        removed_liquidity = 0
        prior_running_liquidity = 0
        prior_positive_liquidity_event_count = 0
        current_round_liquidity_event_count = 0
        current_round_started_at = None
        current_round_started_transaction_id = None
        for row in history:
            liquidity_delta = self.value_support.to_attos(row.get('liquidity')) or 0
            if running_liquidity <= 0:
                current_round_liquidity_event_count = 0
                current_round_started_at = row.get('created_at')
                current_round_started_transaction_id = row.get('transaction_id')
            if row is not latest_transaction and liquidity_delta > 0:
                prior_positive_liquidity_event_count += 1
            if row.get('transaction_type') == 'AddLiquidity':
                running_liquidity += liquidity_delta
                added_liquidity += liquidity_delta
            elif row.get('transaction_type') == 'RemoveLiquidity':
                running_liquidity -= liquidity_delta
                removed_liquidity += liquidity_delta
            current_round_liquidity_event_count += 1
            if row is not latest_transaction:
                prior_running_liquidity = running_liquidity
        status = 'active' if running_liquidity > 0 else 'closed'
        basis_type = self._basis_type(latest_transaction)
        basis_amount_0 = self._basis_amount(latest_transaction, 'amount_0_in', 'amount_0_out')
        basis_amount_1 = self._basis_amount(latest_transaction, 'amount_1_in', 'amount_1_out')
        current_round_started_key = (
            int(current_round_started_at or 0),
            int(current_round_started_transaction_id or 0),
        )
        latest_transaction_key = (
            int(latest_transaction.get('created_at') or 0),
            int(latest_transaction.get('transaction_id') or 0),
        )
        current_round_trade_count_before_basis = sum(
            1
            for row in (pool_trade_history or [])
            if row.get('transaction_type') in {'BuyToken0', 'SellToken0'}
            and (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
            ) >= current_round_started_key
            and (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
            ) < latest_transaction_key
        )
        latest_pool_liquidity_key = latest_transaction_key
        if latest_pool_liquidity_transaction is not None:
            latest_pool_liquidity_key = (
                int(latest_pool_liquidity_transaction.get('created_at') or 0),
                int(latest_pool_liquidity_transaction.get('transaction_id') or 0),
            )
        trade_count_between_basis_and_fee_free_basis = sum(
            1
            for row in (pool_trade_history or [])
            if row.get('transaction_type') in {'BuyToken0', 'SellToken0'}
            and (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
            ) > latest_transaction_key
            and (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
            ) < latest_pool_liquidity_key
        )
        reconstructed_pool_history = self._reconstruct_pool_transaction_history(
            pool_transaction_history=pool_transaction_history,
        )
        exact_current_principal = self._simulate_exact_current_principal(
            reconstructed_pool_history=reconstructed_pool_history,
            latest_position_tx=latest_transaction,
            tracked_liquidity_attos=max(running_liquidity, 0),
            basis_type=basis_type,
            basis_opens_current_round=prior_running_liquidity <= 0,
            current_round_trade_count_before_basis=current_round_trade_count_before_basis,
        )
        protocol_fee_ownership = self._build_protocol_fee_ownership_summary(
            owner=owner,
            reconstructed_pool_history=reconstructed_pool_history,
            latest_position_tx=latest_transaction,
            pool_application_id=pool_application_id,
        )
        if exact_current_principal is not None and protocol_fee_ownership is not None:
            exact_current_principal = {
                **exact_current_principal,
                **protocol_fee_ownership,
            }
        fee_to_continuity = self._build_fee_to_continuity(
            owner=owner,
            pool_application_id=pool_application_id,
            basis_time_ms=latest_transaction.get('created_at'),
            basis_transaction_id=latest_transaction.get('transaction_id'),
        )
        return {
            'position_state_id': f'{owner}:{pool_application_id}:{status}',
            'owner': owner,
            'pool_application_id': pool_application_id,
            'pool_chain_id': pool_chain_id or self._parse_pool_chain_id(pool_application_id),
            'status': status,
            'basis_type': basis_type,
            'current_liquidity': self._serialize_attos(max(running_liquidity, 0)),
            'basis_liquidity': self._serialize_attos(max(running_liquidity, 0)),
            'basis_amount_0': basis_amount_0,
            'basis_amount_1': basis_amount_1,
            'basis_time_ms': latest_transaction.get('created_at'),
            'basis_transaction_id': latest_transaction.get('transaction_id'),
            'source_event_key': self._position_source_event_key(
                owner=owner,
                pool_application_id=pool_application_id,
                transaction_id=latest_transaction.get('transaction_id'),
                created_at=latest_transaction.get('created_at'),
            ),
            'state_payload_json': {
                'latest_liquidity_transaction': latest_transaction,
                'history_size': len(history),
                'added_liquidity': self._serialize_attos(added_liquidity),
                'removed_liquidity': self._serialize_attos(removed_liquidity),
                'prior_liquidity_before_basis': self._serialize_attos(max(prior_running_liquidity, 0)),
                'basis_opens_current_round': prior_running_liquidity <= 0,
                'has_only_zero_liquidity_before_basis': prior_positive_liquidity_event_count == 0,
                'current_round_liquidity_event_count': current_round_liquidity_event_count,
                'current_round_started_at': current_round_started_at,
                'current_round_started_transaction_id': current_round_started_transaction_id,
                'current_round_trade_count_before_basis': current_round_trade_count_before_basis,
                'trade_count_between_basis_and_fee_free_basis': trade_count_between_basis_and_fee_free_basis,
                'exact_current_principal': exact_current_principal,
                'fee_to_continuity': fee_to_continuity,
                'current_liquidity': self._serialize_attos(max(running_liquidity, 0)),
            },
        }

    def _collect_affected_pools(
        self,
        outputs: list[dict[str, object]],
    ) -> list[tuple[str, str | None]]:
        pools = {
            (str(output['pool_application_id']), self._string_or_none(output.get('pool_chain_id')))
            for output in outputs
            if output.get('pool_application_id') is not None
        }
        return sorted(pools)

    def _collect_affected_positions(
        self,
        outputs: list[dict[str, object]],
    ) -> list[tuple[str, str, str | None]]:
        positions = {
            (
                self._public_owner(str(output['owner'])),
                str(output['pool_application_id']),
                self._string_or_none(output.get('pool_chain_id')),
            )
            for output in outputs
            if output.get('settled_output_type') == 'settled_liquidity_change'
            and output.get('owner') is not None
            and output.get('pool_application_id') is not None
        }
        return sorted(positions)

    def _load_pool_transaction_history(
        self,
        *,
        pool_application_id: str,
    ) -> list[dict[str, object]]:
        history = []
        history.extend(
            self.snapshot_source_repository.list_pool_trade_history(
                pool_application_id=pool_application_id,
            )
        )
        history.extend(
            self.snapshot_source_repository.list_pool_liquidity_history(
                pool_application_id=pool_application_id,
            )
        )
        history.sort(
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
                row.get('transaction_type') or '',
            ),
        )
        return history

    def _reconstructor(self) -> PositionMetricsPoolHistoryReconstructor:
        return PositionMetricsPoolHistoryReconstructor(
            to_attos=self.value_support.to_attos,
            swap_expected_out_attos=self.swap_math_support.swap_expected_out_attos,
            swap_out_within_tolerance=self.value_support.swap_out_within_tolerance,
            infer_hidden_swap_before_batch=self.swap_math_support.infer_hidden_swap_before_batch,
            apply_recorded_swap_attos=self.swap_math_support.apply_recorded_swap_attos,
            sqrt_attos_product=self.swap_math_support.sqrt_attos_product,
            mint_fee_attos=self.swap_math_support.mint_fee_attos,
            attos_within_tolerance=self.value_support.attos_within_tolerance,
        )

    def _effective_total_supply_attos(self, state: dict[str, object]) -> int:
        total_supply_after = int(state.get('total_supply_after') or 0)
        reserve0_after = int(state.get('reserve0_after') or 0)
        reserve1_after = int(state.get('reserve1_after') or 0)
        k_last_after = int(state.get('k_last_after') or 0)
        return total_supply_after + self.swap_math_support.mint_fee_attos(
            total_supply_after,
            reserve0_after,
            reserve1_after,
            k_last_after,
        )

    def _fee_free_swap_expected_out_attos(
        self,
        tx_type: str,
        reserve0: int,
        reserve1: int,
        amount0_in: int,
        amount1_in: int,
    ) -> int | None:
        if reserve0 <= 0 or reserve1 <= 0:
            return None
        if tx_type == 'BuyToken0':
            if amount1_in <= 0:
                return None
            return amount1_in * reserve0 // (reserve1 + amount1_in)
        if tx_type == 'SellToken0':
            if amount0_in <= 0:
                return None
            return amount0_in * reserve1 // (reserve0 + amount0_in)
        return None

    def _infer_virtual_initial_liquidity(
        self,
        history: list[dict[str, object]],
    ) -> bool:
        for row in history:
            if row.get('transaction_type') != 'AddLiquidity':
                continue
            liquidity_attos = self.value_support.to_attos(row.get('liquidity')) or 0
            return liquidity_attos == 0
        return False

    def _basis_type(self, row: dict[str, object]) -> str:
        if row.get('transaction_type') == 'AddLiquidity':
            return 'add_liquidity'
        return 'remove_liquidity'

    def _basis_amount(
        self,
        row: dict[str, object],
        add_key: str,
        remove_key: str,
    ) -> str:
        value = row.get(add_key) if row.get('transaction_type') == 'AddLiquidity' else row.get(remove_key)
        if value is None:
            return '0'
        return str(value)

    def _serialize_attos(self, value: int | None) -> str:
        decimal_value = self.value_support.from_attos(value or 0) or Decimal('0')
        return self.value_support.serialize_decimal(decimal_value) or '0'

    def _parse_pool_chain_id(self, pool_application_id: str) -> str | None:
        if ':' not in pool_application_id:
            return None
        return pool_application_id.split(':', 1)[0]

    def _pool_source_event_key(
        self,
        *,
        pool_application_id: str,
        last_transaction_id: int | None,
        last_trade_time_ms: int | None,
        last_liquidity_event_time_ms: int | None,
    ) -> str:
        suffix = last_transaction_id
        if suffix is None:
            suffix = last_trade_time_ms if last_trade_time_ms is not None else last_liquidity_event_time_ms
        return f'{pool_application_id}:{suffix or "snapshot"}'

    def _position_source_event_key(
        self,
        *,
        owner: str,
        pool_application_id: str,
        transaction_id: object,
        created_at: object,
    ) -> str:
        suffix = transaction_id if transaction_id is not None else created_at
        return f'{owner}:{pool_application_id}:{suffix or "snapshot"}'

    def _latest_row(self, rows: list[dict[str, object]] | None) -> dict[str, object] | None:
        if not rows:
            return None
        return max(
            rows,
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
                str(row.get('transaction_type') or ''),
            ),
        )

    def _simulate_exact_current_principal(
        self,
        *,
        reconstructed_pool_history: dict[str, object] | None,
        latest_position_tx: dict[str, object],
        tracked_liquidity_attos: int,
        basis_type: str,
        basis_opens_current_round: bool,
        current_round_trade_count_before_basis: int,
    ) -> dict[str, object] | None:
        if reconstructed_pool_history is None:
            return None
        effective_history = reconstructed_pool_history['effective_history']
        states = reconstructed_pool_history['states']
        blockers = reconstructed_pool_history['blockers']
        if blockers or not effective_history or not states:
            return None
        return self.principal_simulator.simulate_current_principal(
            effective_history=effective_history,
            states=states,
            latest_position_tx=latest_position_tx,
            tracked_liquidity_attos=tracked_liquidity_attos,
            basis_type=basis_type,
            basis_opens_current_round=basis_opens_current_round,
            current_round_trade_count_before_basis=current_round_trade_count_before_basis,
        )

    def _build_protocol_fee_ownership_summary(
        self,
        *,
        owner: str,
        reconstructed_pool_history: dict[str, object] | None,
        latest_position_tx: dict[str, object],
        pool_application_id: str,
    ) -> dict[str, object] | None:
        if reconstructed_pool_history is None:
            return None
        effective_history = reconstructed_pool_history['effective_history']
        states = reconstructed_pool_history['states']
        blockers = reconstructed_pool_history['blockers']
        if blockers or not effective_history or not states:
            return None
        fee_to_history = None
        if hasattr(self.snapshot_source_repository, 'list_pool_fee_to_history'):
            fee_to_history = self.snapshot_source_repository.list_pool_fee_to_history(
                pool_application_id=pool_application_id,
            )
        return self.protocol_fee_ownership_tracker.summarize(
            owner=owner,
            effective_history=effective_history,
            states=states,
            latest_position_tx=latest_position_tx,
            fee_to_history=fee_to_history,
        )

    def _reconstruct_pool_transaction_history(
        self,
        *,
        pool_transaction_history: list[dict[str, object]],
    ) -> dict[str, object]:
        effective_history, states, blockers = self._reconstructor().reconstruct(
            pool_transaction_history,
            virtual_initial_liquidity=self._infer_virtual_initial_liquidity(pool_transaction_history),
        )
        return {
            'effective_history': effective_history,
            'states': states,
            'blockers': blockers,
        }

    def _string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def _build_fee_to_continuity(
        self,
        *,
        owner: str,
        pool_application_id: str,
        basis_time_ms: object,
        basis_transaction_id: object,
    ) -> dict[str, object]:
        if not hasattr(self.snapshot_source_repository, 'list_pool_fee_to_history'):
            return {'continuity_case': 'unsupported_source', 'owner': owner}
        history = self.snapshot_source_repository.list_pool_fee_to_history(
            pool_application_id=pool_application_id,
        )
        basis_key = (
            int(basis_time_ms or 0),
            int(basis_transaction_id or 0),
        )
        history = sorted(
            history or [],
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
                str(row.get('fee_to_account') or ''),
            ),
        )
        latest_before_or_at_basis = None
        latest_overall = None
        change_count_after_basis = 0
        for row in history:
            row_key = (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
            )
            latest_overall = row
            if row_key <= basis_key:
                latest_before_or_at_basis = row
            elif row.get('fee_to_account') is not None:
                change_count_after_basis += 1
        if latest_before_or_at_basis is None:
            continuity_case = 'unknown_missing_pre_basis_anchor'
        elif change_count_after_basis > 0:
            continuity_case = 'changed_after_basis'
        else:
            continuity_case = 'continuous_no_changes_after_basis'
        return {
            'continuity_case': continuity_case,
            'owner': owner,
            'change_count_after_basis': change_count_after_basis,
            'known_before_basis': latest_before_or_at_basis is not None,
            'fee_to_account_at_basis': (
                latest_before_or_at_basis.get('fee_to_account') if latest_before_or_at_basis is not None else None
            ),
            'fee_to_account_latest_known': (
                latest_overall.get('fee_to_account') if latest_overall is not None else None
            ),
            'latest_change_time_ms': (
                latest_overall.get('created_at') if latest_overall is not None else None
            ),
            'latest_change_transaction_id': (
                latest_overall.get('transaction_id') if latest_overall is not None else None
            ),
            'history_size': len(history),
        }

    def _fee_free_state_from_latest_liquidity_event(
        self,
        *,
        states: list[dict[str, object]],
        effective_history: list[dict[str, object]],
    ) -> tuple[dict[str, int], dict[str, object] | None]:
        latest_liquidity_index = None
        for index, row in enumerate(effective_history):
            if row.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}:
                latest_liquidity_index = index
        if latest_liquidity_index is None:
            latest_state = states[-1]
            return {
                'reserve0': int(latest_state['reserve0_after']),
                'reserve1': int(latest_state['reserve1_after']),
            }, None
        basis_state = states[latest_liquidity_index]
        reserve0 = int(basis_state['reserve0_after'])
        reserve1 = int(basis_state['reserve1_after'])
        for row in effective_history[latest_liquidity_index + 1:]:
            transaction_type = row.get('transaction_type')
            if transaction_type == 'BuyToken0':
                amount1_in = self.value_support.to_attos(row.get('amount_1_in')) or 0
                if amount1_in <= 0:
                    continue
                amount0_out = amount1_in * reserve0 // (reserve1 + amount1_in)
                reserve1 += amount1_in
                reserve0 -= amount0_out
            elif transaction_type == 'SellToken0':
                amount0_in = self.value_support.to_attos(row.get('amount_0_in')) or 0
                if amount0_in <= 0:
                    continue
                amount1_out = amount0_in * reserve1 // (reserve0 + amount0_in)
                reserve0 += amount0_in
                reserve1 -= amount1_out
        return {
            'reserve0': reserve0,
            'reserve1': reserve1,
        }, basis_state

    def _public_owner(self, owner: str) -> str:
        if '@' not in owner:
            return owner
        owner_id, chain_id = owner.split('@', 1)
        return f'{chain_id}:{owner_id}'
