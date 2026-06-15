from decimal import Decimal

from account_codec import AccountCodec
from market.position_metrics_protocol_fee_ownership_tracker import PositionMetricsProtocolFeeOwnershipTracker
from market.position_metrics_snapshot_principal_simulator import PositionMetricsSnapshotPrincipalSimulator
from position_metrics_pool_history_reconstructor import PositionMetricsPoolHistoryReconstructor
from position_metrics_swap_math_support import PositionMetricsSwapMathSupport
from position_metrics_value_support import PositionMetricsValueSupport


class PositionMetricsSnapshotBuilder:
    def __init__(
        self,
        *,
        snapshot_materialization_inputs_repository,
        attos_scale: int = 10 ** 18,
        swap_fee_numerator: int = 997,
        swap_fee_denominator: int = 1000,
        display_quantum: Decimal = Decimal('0.000000000000000001'),
        epsilon: Decimal = Decimal('0.000000000001'),
        liquidity_mint_tolerance_attos: int = 100,
        swap_out_tolerance_attos: int = 1,
    ):
        self.snapshot_materialization_inputs_repository = snapshot_materialization_inputs_repository
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
        self.account_codec = AccountCodec()

    def apply_pool_state(self, state, output):
        created_at = int(output.get('created_at') or output.get('event_time_ms') or output.get('trade_time_ms') or 0)
        tx_id = int(output.get('transaction_id') or 0)

        if output.get('settled_output_type') == 'settled_trade':
            return self._apply_trade(state, output, created_at, tx_id)
        if output.get('settled_output_type') == 'settled_liquidity_change':
            return self._apply_liquidity(state, output, created_at, tx_id)
        return state

    def _apply_trade(self, state, output, created_at, tx_id):
        tx_type = self._trade_transaction_type(output)
        raw_amounts = self._uses_raw_settled_trade_amounts(output)
        amount0_in = self._amount_attos(output.get('amount_0_in'), raw=raw_amounts)
        amount0_out = self._amount_attos(output.get('amount_0_out'), raw=raw_amounts)
        amount1_in = self._amount_attos(output.get('amount_1_in'), raw=raw_amounts)
        amount1_out = self._amount_attos(output.get('amount_1_out'), raw=raw_amounts)

        reserve0, reserve1 = self.swap_math_support.apply_recorded_swap_attos(
            tx_type, state['reserve0'], state['reserve1'],
            amount0_in=amount0_in, amount0_out=amount0_out,
            amount1_in=amount1_in, amount1_out=amount1_out,
        )
        state['reserve0'] = max(reserve0, 0)
        state['reserve1'] = max(reserve1, 0)
        self._apply_fee_free_trade_state(
            state,
            tx_type=tx_type,
            amount0_in=amount0_in,
            amount1_in=amount1_in,
        )
        state['pending_protocol_fee'] = self.swap_math_support.mint_fee_attos(
            state['total_supply'], state['reserve0'], state['reserve1'], state['k_last'],
        )
        state['swap_count'] = state.get('swap_count', 0) + 1
        state['last_trade_time_ms'] = created_at
        state['last_transaction_id'] = max(state.get('last_transaction_id') or 0, tx_id)
        return state

    def _apply_fee_free_trade_state(
        self,
        state,
        *,
        tx_type: str,
        amount0_in: int,
        amount1_in: int,
    ) -> None:
        fee_free_reserve0 = state.get('fee_free_reserve0')
        fee_free_reserve1 = state.get('fee_free_reserve1')
        if fee_free_reserve0 is None or fee_free_reserve1 is None:
            return
        if fee_free_reserve0 <= 0 or fee_free_reserve1 <= 0:
            return
        expected_out = self._fee_free_swap_expected_out_attos(
            tx_type,
            fee_free_reserve0,
            fee_free_reserve1,
            amount0_in,
            amount1_in,
        )
        if expected_out is None:
            return
        if tx_type == 'BuyToken0':
            state['fee_free_reserve0'] = max(fee_free_reserve0 - expected_out, 0)
            state['fee_free_reserve1'] = fee_free_reserve1 + amount1_in
            return
        if tx_type == 'SellToken0':
            state['fee_free_reserve0'] = fee_free_reserve0 + amount0_in
            state['fee_free_reserve1'] = max(fee_free_reserve1 - expected_out, 0)

    def _apply_liquidity(self, state, output, created_at, tx_id):
        tx_type = self._liquidity_transaction_type(output)
        liquidity = self._liquidity_attos(output)
        amount0_delta = output.get('amount_0_delta')
        amount1_delta = output.get('amount_1_delta')
        amount0_in = self._liquidity_amount_attos(
            output, display_key='amount_0_in', delta_value=amount0_delta,
            use_delta=tx_type == 'AddLiquidity',
        )
        amount0_out = self._liquidity_amount_attos(
            output, display_key='amount_0_out', delta_value=amount0_delta,
            use_delta=tx_type == 'RemoveLiquidity',
        )
        amount1_in = self._liquidity_amount_attos(
            output, display_key='amount_1_in', delta_value=amount1_delta,
            use_delta=tx_type == 'AddLiquidity',
        )
        amount1_out = self._liquidity_amount_attos(
            output, display_key='amount_1_out', delta_value=amount1_delta,
            use_delta=tx_type == 'RemoveLiquidity',
        )
        is_add = tx_type == 'AddLiquidity'
        is_virtual_init = (
            is_add and state['reserve0'] == 0 and state['reserve1'] == 0
            and output.get('liquidity_semantics') == 'virtual_initial_liquidity'
        )

        if is_virtual_init:
            state['total_supply'] = (
                self.swap_math_support.sqrt_attos_product(amount0_in, amount1_in) or 0
            )
        else:
            mint = state['pending_protocol_fee']
            state['total_minted_protocol_fee'] = state.get('total_minted_protocol_fee', 0) + mint
            state['pending_protocol_fee'] = max(0, state['pending_protocol_fee'] - mint)
            state['total_supply'] += mint + (liquidity if is_add else -liquidity)

        if is_add:
            state['reserve0'] += amount0_in
            state['reserve1'] += amount1_in
        else:
            state['reserve0'] = max(state['reserve0'] - amount0_out, 0)
            state['reserve1'] = max(state['reserve1'] - amount1_out, 0)

        state['k_last'] = (
            self.swap_math_support.sqrt_attos_product(state['reserve0'], state['reserve1']) or 0
        )
        state['last_liquidity_event_time_ms'] = created_at
        state['last_transaction_id'] = max(state.get('last_transaction_id') or 0, tx_id)
        state['fee_free_basis_transaction_id'] = tx_id
        state['fee_free_basis_time_ms'] = created_at
        state['fee_free_reserve0'] = state['reserve0']
        state['fee_free_reserve1'] = state['reserve1']
        state['fee_free_total_supply'] = state['total_supply']
        return state

    def apply_position_state(self, state, output):
        tx_type = self._liquidity_transaction_type(output)
        liquidity = self._liquidity_attos(output)
        created_at = int(output.get('created_at') or output.get('event_time_ms') or 0)
        tx_id = int(output.get('transaction_id') or 0)
        is_add = tx_type == 'AddLiquidity'
        amount0_delta = output.get('amount_0_delta')
        amount1_delta = output.get('amount_1_delta')

        if state.get('running_liquidity', 0) <= 0:
            state['current_round_liquidity_event_count'] = 0
            state['current_round_started_at'] = created_at
            state['current_round_started_transaction_id'] = tx_id

        if is_add:
            state['running_liquidity'] = state.get('running_liquidity', 0) + liquidity
            state['added_liquidity'] = state.get('added_liquidity', 0) + liquidity
            state['basis_amount_0'] = self._position_basis_amount(
                output, display_key='amount_0_in', delta_value=amount0_delta,
            )
            state['basis_amount_1'] = self._position_basis_amount(
                output, display_key='amount_1_in', delta_value=amount1_delta,
            )
        else:
            state['running_liquidity'] = state.get('running_liquidity', 0) - liquidity
            state['removed_liquidity'] = state.get('removed_liquidity', 0) + liquidity
            state['basis_amount_0'] = self._position_basis_amount(
                output, display_key='amount_0_out', delta_value=amount0_delta,
            )
            state['basis_amount_1'] = self._position_basis_amount(
                output, display_key='amount_1_out', delta_value=amount1_delta,
            )

        state['current_liquidity'] = max(state.get('running_liquidity', 0), 0)
        state['status'] = 'active' if state.get('running_liquidity', 0) > 0 else 'closed'
        state['basis_type'] = self._basis_type({'transaction_type': tx_type})
        state['basis_time_ms'] = created_at
        state['basis_transaction_id'] = tx_id
        state['current_round_liquidity_event_count'] = (
            state.get('current_round_liquidity_event_count', 0) + 1
        )
        state['last_transaction_id'] = max(
            state.get('last_transaction_id', 0), tx_id
        )
        return state

    def _trade_transaction_type(self, output):
        transaction_type = output.get('transaction_type')
        if transaction_type is not None:
            return transaction_type
        side = output.get('side')
        if side == 'buy_token_0':
            return 'BuyToken0'
        if side == 'sell_token_0':
            return 'SellToken0'
        return None

    def _liquidity_transaction_type(self, output):
        transaction_type = output.get('transaction_type')
        if transaction_type is not None:
            return transaction_type
        change_type = output.get('change_type')
        if change_type == 'add_liquidity':
            return 'AddLiquidity'
        if change_type == 'remove_liquidity':
            return 'RemoveLiquidity'
        return None

    def _uses_raw_settled_trade_amounts(self, output) -> bool:
        return (
            output.get('settled_output_type') == 'settled_trade'
            and output.get('side') is not None
            and output.get('transaction_type') is None
        )

    def _liquidity_attos(self, output) -> int:
        if output.get('liquidity_delta') is not None:
            return self._amount_attos(output.get('liquidity_delta'), raw=True)
        return self._amount_attos(output.get('liquidity'), raw=False)

    def _liquidity_amount_attos(
        self,
        output,
        *,
        display_key: str,
        delta_value,
        use_delta: bool,
    ) -> int:
        if output.get(display_key) is not None:
            return self._amount_attos(output.get(display_key), raw=False)
        if use_delta:
            return self._amount_attos(delta_value, raw=True)
        return 0

    def _position_basis_amount(
        self,
        output,
        *,
        display_key: str,
        delta_value,
    ) -> str:
        if output.get(display_key) is not None:
            return str(output.get(display_key))
        if delta_value is None:
            return '0'
        return self._serialize_attos(self._amount_attos(delta_value, raw=True))

    def _amount_attos(self, value, *, raw: bool) -> int:
        if raw:
            decimal_value = self.value_support.to_decimal(value)
            if decimal_value is None:
                return 0
            return int(decimal_value.to_integral_value())
        return self.value_support.to_attos(value) or 0

    def _build_pool_state(
        self,
        *,
        pool_application_id: str,
        pool_chain_id: str | None,
    ) -> dict[str, object] | None:
        history = self._load_pool_transaction_history(
            pool_application_id=pool_application_id,
            pool_chain_id=pool_chain_id,
        )
        if not history:
            return None
        virtual_initial_liquidity = self._infer_virtual_initial_liquidity(history)

        state = {
            'reserve0': 0, 'reserve1': 0,
            'total_supply': 0, 'k_last': 0,
            'pending_protocol_fee': 0, 'total_minted_protocol_fee': 0,
            'swap_count': 0,
            'last_trade_time_ms': 0, 'last_liquidity_event_time_ms': 0,
            'last_transaction_id': 0,
            'fee_free_basis_transaction_id': None,
            'fee_free_basis_time_ms': None,
            'fee_free_reserve0': 0,
            'fee_free_reserve1': 0,
            'fee_free_total_supply': 0,
        }

        for row in history:
            tx_type = row.get('transaction_type')
            output = dict(row)
            if tx_type in ('BuyToken0', 'SellToken0'):
                output['settled_output_type'] = 'settled_trade'
                output['trade_time_ms'] = row.get('created_at')
            elif tx_type in ('AddLiquidity', 'RemoveLiquidity'):
                output['settled_output_type'] = 'settled_liquidity_change'
            else:
                continue
            if (
                virtual_initial_liquidity
                and tx_type == 'AddLiquidity'
                and state['reserve0'] == 0
                and state['reserve1'] == 0
            ):
                output['liquidity_semantics'] = 'virtual_initial_liquidity'
            state = self.apply_pool_state(state, output)

        snapshot_pool_application_id = self._canonical_pool_application(
            pool_application_id=pool_application_id,
            pool_chain_id=pool_chain_id,
        )
        tx_id = state.get('last_transaction_id')
        return {
            'pool_state_id': snapshot_pool_application_id,
            'pool_application_id': snapshot_pool_application_id,
            'pool_chain_id': pool_chain_id or self._parse_pool_chain_id(
                snapshot_pool_application_id
            ),
            'last_trade_time_ms': state.get('last_trade_time_ms'),
            'last_liquidity_event_time_ms': state.get('last_liquidity_event_time_ms'),
            'last_transaction_id': tx_id,
            'swap_count': state.get('swap_count', 0),
            'current_reserve_0': self._serialize_attos(state['reserve0']),
            'current_reserve_1': self._serialize_attos(state['reserve1']),
            'current_total_supply': self._serialize_attos(state['total_supply']),
            'current_k_last': self._serialize_attos(state['k_last']),
            'total_minted_protocol_fee': self._serialize_attos(
                state.get('total_minted_protocol_fee', 0)
            ),
            'pending_protocol_fee': self._serialize_attos(
                state.get('pending_protocol_fee', 0)
            ),
            'fee_free_basis_transaction_id': state.get('fee_free_basis_transaction_id'),
            'fee_free_basis_time_ms': state.get('fee_free_basis_time_ms'),
            'fee_free_reserve_0': self._serialize_attos(state.get('fee_free_reserve0', 0)),
            'fee_free_reserve_1': self._serialize_attos(state.get('fee_free_reserve1', 0)),
            'fee_free_total_supply': self._serialize_attos(state.get('fee_free_total_supply', 0)),
            'source_event_key': self._pool_source_event_key(
                pool_application_id=pool_application_id,
                last_transaction_id=tx_id,
                last_trade_time_ms=state.get('last_trade_time_ms'),
                last_liquidity_event_time_ms=state.get('last_liquidity_event_time_ms'),
            ),
            'state_payload_json': {
                'virtual_initial_liquidity': virtual_initial_liquidity,
                'fee_to_account_latest_known': self._pool_fee_to_account_latest_known(
                    pool_application_id=pool_application_id,
                ),
                'history_size': len(history),
            },
        }

    def _build_position_state(
        self,
        *,
        owner: str,
        pool_application_id: str,
        pool_chain_id: str | None,
    ) -> dict[str, object] | None:
        history = self.snapshot_materialization_inputs_repository.list_position_liquidity_history(
            owner=owner,
            pool_application_id=self._canonical_pool_application(
                pool_application_id=pool_application_id,
                pool_chain_id=pool_chain_id,
            ),
        )
        if not history:
            return None
        pool_transaction_history = self._load_pool_transaction_history(
            pool_application_id=pool_application_id,
            pool_chain_id=pool_chain_id,
        )
        pool_trade_history = [
            row
            for row in pool_transaction_history
            if row.get('transaction_type') in {'BuyToken0', 'SellToken0'}
        ]
        pool_liquidity_history = [
            row
            for row in pool_transaction_history
            if row.get('transaction_type') in {'AddLiquidity', 'RemoveLiquidity'}
        ]
        latest_transaction = history[-1]
        latest_pool_liquidity_transaction = self._latest_row(pool_liquidity_history)
        state = {
            'running_liquidity': 0, 'current_liquidity': 0,
            'added_liquidity': 0, 'removed_liquidity': 0,
            'status': None,
            'current_round_liquidity_event_count': 0,
            'current_round_started_at': None,
            'current_round_started_transaction_id': None,
        }
        prior_positive_liquidity_event_count = 0
        prior_running_liquidity = 0
        prev_state = None

        for index, row in enumerate(history):
            if index == len(history) - 1:
                prev_state = dict(state)
                prior_positive_liquidity_event_count = sum(
                    1 for j in range(index)
                    if history[j].get('transaction_type') == 'AddLiquidity'
                    and (self.value_support.to_attos(history[j].get('liquidity')) or 0) > 0
                )
            output = dict(row)
            output['settled_output_type'] = 'settled_liquidity_change'
            state = self.apply_position_state(state, output)

        if prev_state is not None:
            prior_running_liquidity = prev_state.get('running_liquidity', 0)

        status = state.get('status') or 'closed'
        basis_type = state.get('basis_type')
        basis_amount_0 = state.get('basis_amount_0', '0')
        basis_amount_1 = state.get('basis_amount_1', '0')
        running_liquidity = state.get('running_liquidity', 0)
        added_liquidity = state.get('added_liquidity', 0)
        removed_liquidity = state.get('removed_liquidity', 0)
        current_round_liquidity_event_count = state.get('current_round_liquidity_event_count', 0)
        current_round_started_at = state.get('current_round_started_at')
        current_round_started_transaction_id = state.get('current_round_started_transaction_id')
        current_round_start_transaction = self._find_row_by_key(
            history,
            current_round_started_transaction_id,
            current_round_started_at,
        )
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
        virtual_initial = self._infer_virtual_initial_liquidity(pool_transaction_history)
        recorded_history, recorded_states = self._reconstruct_recorded_pool_state_history(
            history=pool_transaction_history,
            virtual_initial_liquidity=virtual_initial,
        )
        recorded_reconstruction = {
            'effective_history': recorded_history,
            'states': recorded_states,
            'blockers': [],
        }
        principal_basis_transaction = latest_transaction
        principal_basis_type = basis_type
        principal_basis_opens_current_round = prior_running_liquidity <= 0
        principal_round_trade_count_before_basis = current_round_trade_count_before_basis
        if (
            latest_transaction.get('transaction_type') == 'RemoveLiquidity'
            and prior_positive_liquidity_event_count == 1
            and current_round_start_transaction is not None
        ):
            principal_basis_transaction = current_round_start_transaction
            principal_basis_type = self._basis_type(current_round_start_transaction)
            principal_basis_opens_current_round = True
            principal_round_trade_count_before_basis = 0
        exact_current_principal = self._simulate_exact_current_principal(
            reconstructed_pool_history=reconstructed_pool_history,
            latest_position_tx=principal_basis_transaction,
            tracked_liquidity_attos=max(running_liquidity, 0),
            basis_type=principal_basis_type,
            basis_opens_current_round=principal_basis_opens_current_round,
            current_round_trade_count_before_basis=principal_round_trade_count_before_basis,
        )
        protocol_fee_ownership = self._build_protocol_fee_ownership_summary(
            owner=owner,
            reconstructed_pool_history=recorded_reconstruction,
            latest_position_tx=latest_transaction,
            pool_application_id=pool_application_id,
        )
        if exact_current_principal is not None and protocol_fee_ownership is not None:
            exact_current_principal = {
                **exact_current_principal,
                **self._build_trailing_24h_fee_summary(
                    exact_current_principal=exact_current_principal,
                    reconstructed_pool_history=reconstructed_pool_history,
                    latest_position_tx=principal_basis_transaction,
                    tracked_liquidity_attos=max(running_liquidity, 0),
                    basis_type=principal_basis_type,
                    basis_opens_current_round=principal_basis_opens_current_round,
                    current_round_trade_count_before_basis=principal_round_trade_count_before_basis,
                ),
                **protocol_fee_ownership,
            }
        fee_to_continuity = self._build_fee_to_continuity(
            owner=owner,
            pool_application_id=pool_application_id,
            basis_time_ms=latest_transaction.get('created_at'),
            basis_transaction_id=latest_transaction.get('transaction_id'),
        )
        snapshot_pool_application_id = self._canonical_pool_application(
            pool_application_id=pool_application_id,
            pool_chain_id=pool_chain_id,
        )
        return {
            'position_state_id': f'{owner}:{snapshot_pool_application_id}:{status}',
            'owner': owner,
            'pool_application_id': snapshot_pool_application_id,
            'pool_chain_id': pool_chain_id or self._parse_pool_chain_id(snapshot_pool_application_id),
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
                'position_liquidity_over_removed': running_liquidity < 0,
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
        output_batch,
    ) -> list[tuple[str, str | None]]:
        return output_batch.affected_pools()

    def _collect_affected_positions(
        self,
        output_batch,
    ) -> list[tuple[str, str, str | None]]:
        affected = set(output_batch.affected_positions())
        affected_pools = output_batch.affected_pools()
        for pool_application_id, pool_chain_id in affected_pools:
            snapshot_pool_application_id = self._canonical_pool_application(
                pool_application_id=pool_application_id,
                pool_chain_id=pool_chain_id,
            )
            active_owners = self.snapshot_materialization_inputs_repository.list_active_position_owners_for_pool(
                pool_application=snapshot_pool_application_id,
            )
            for owner in active_owners:
                affected.add((owner, snapshot_pool_application_id, pool_chain_id))
        return sorted(affected)

    def _load_pool_transaction_history(
        self,
        *,
        pool_application_id: str,
        pool_chain_id: str | None = None,
    ) -> list[dict[str, object]]:
        history = list(
            self.snapshot_materialization_inputs_repository.list_pool_transaction_history(
                pool_application_id=pool_application_id,
                pool_chain_id=pool_chain_id,
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

    def _reconstruct_recorded_pool_state_history(
        self,
        *,
        history: list[dict[str, object]],
        virtual_initial_liquidity: bool,
    ) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        reserve0 = 0
        reserve1 = 0
        total_supply = 0
        k_last = 0
        effective_history = []
        states = []
        for row in history:
            transaction_type = row.get('transaction_type')
            amount0_in = self.value_support.to_attos(row.get('amount_0_in')) or 0
            amount0_out = self.value_support.to_attos(row.get('amount_0_out')) or 0
            amount1_in = self.value_support.to_attos(row.get('amount_1_in')) or 0
            amount1_out = self.value_support.to_attos(row.get('amount_1_out')) or 0
            liquidity = self.value_support.to_attos(row.get('liquidity')) or 0
            protocol_fee_minted = 0
            if transaction_type == 'AddLiquidity':
                if reserve0 == 0 and reserve1 == 0 and virtual_initial_liquidity and liquidity == 0:
                    total_supply = self.swap_math_support.sqrt_attos_product(amount0_in, amount1_in) or 0
                else:
                    protocol_fee_minted = self.swap_math_support.mint_fee_attos(
                        total_supply,
                        reserve0,
                        reserve1,
                        k_last,
                    )
                    total_supply += protocol_fee_minted + liquidity
                reserve0 += amount0_in
                reserve1 += amount1_in
                k_last = self.swap_math_support.sqrt_attos_product(reserve0, reserve1) or 0
            elif transaction_type == 'RemoveLiquidity':
                protocol_fee_minted = self.swap_math_support.mint_fee_attos(
                    total_supply,
                    reserve0,
                    reserve1,
                    k_last,
                )
                total_supply += protocol_fee_minted
                total_supply = max(total_supply - liquidity, 0)
                reserve0 = max(reserve0 - amount0_out, 0)
                reserve1 = max(reserve1 - amount1_out, 0)
                k_last = self.swap_math_support.sqrt_attos_product(reserve0, reserve1) or 0
            elif transaction_type in {'BuyToken0', 'SellToken0'}:
                reserve0, reserve1 = self.swap_math_support.apply_recorded_swap_attos(
                    transaction_type,
                    reserve0,
                    reserve1,
                    amount0_in=amount0_in,
                    amount0_out=amount0_out,
                    amount1_in=amount1_in,
                    amount1_out=amount1_out,
                )
                reserve0 = max(reserve0, 0)
                reserve1 = max(reserve1, 0)
            else:
                continue
            effective_history.append(row)
            states.append({
                'transaction_id': row.get('transaction_id'),
                'created_at': row.get('created_at'),
                'transaction_type': transaction_type,
                'from_account': row.get('from_account'),
                'reserve0_after': reserve0,
                'reserve1_after': reserve1,
                'total_supply_after': total_supply,
                'k_last_after': k_last,
                'protocol_fee_minted_after': protocol_fee_minted,
            })
        return effective_history, states

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
            return row.get('liquidity_semantics') == 'virtual_initial_liquidity'
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
        try:
            return self.account_codec.chain_id_from_account(pool_application_id)
        except ValueError:
            return None

    def _canonical_pool_application(
        self,
        *,
        pool_application_id: str,
        pool_chain_id: str | None,
    ) -> str:
        parsed = self.account_codec.parse_account(pool_application_id)
        return self.account_codec.format_account(
            chain_id=parsed['chain_id'],
            owner=parsed['owner'],
        )

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

    def _find_row_by_key(
        self,
        rows: list[dict[str, object]],
        transaction_id: object,
        created_at: object,
    ) -> dict[str, object] | None:
        target_key = (int(created_at or 0), int(transaction_id or 0))
        for row in rows:
            row_key = (int(row.get('created_at') or 0), int(row.get('transaction_id') or 0))
            if row_key == target_key:
                return row
        return None

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

    def _build_trailing_24h_fee_summary(
        self,
        *,
        exact_current_principal: dict[str, object],
        reconstructed_pool_history: dict[str, object] | None,
        latest_position_tx: dict[str, object],
        tracked_liquidity_attos: int,
        basis_type: str,
        basis_opens_current_round: bool,
        current_round_trade_count_before_basis: int,
    ) -> dict[str, object]:
        states = (reconstructed_pool_history or {}).get('states') or []
        effective_history = (reconstructed_pool_history or {}).get('effective_history') or []
        current_time_ms = int((states[-1] if states else {}).get('created_at') or 0)
        window_start_ms = current_time_ms - 86400000
        empty_summary = {
            'trailing_24h_fee_amount_0': '0',
            'trailing_24h_fee_amount_1': '0',
            'trailing_24h_fee_window_start_ms': window_start_ms,
            'trailing_24h_fee_window_end_ms': current_time_ms,
        }
        if not states or not effective_history or tracked_liquidity_attos <= 0:
            return empty_summary
        current_principal_0 = self.value_support.to_attos(
            exact_current_principal.get('principal_amount_0_current')
        )
        current_principal_1 = self.value_support.to_attos(
            exact_current_principal.get('principal_amount_1_current')
        )
        if current_principal_0 is None or current_principal_1 is None:
            return {}
        current_fee_0, current_fee_1 = self._position_fee_at_state(
            state=states[-1],
            tracked_liquidity_attos=tracked_liquidity_attos,
            principal_0_attos=current_principal_0,
            principal_1_attos=current_principal_1,
        )
        baseline_index = self._latest_state_index_before(
            exact_states=states,
            created_at_ms=window_start_ms,
        )
        if baseline_index is None:
            baseline_index = self._state_index_for_transaction(
                exact_states=states,
                transaction=latest_position_tx,
            )
        if baseline_index is None:
            return empty_summary
        basis_index = self._state_index_for_transaction(
            exact_states=states,
            transaction=latest_position_tx,
        )
        if basis_index is None:
            return empty_summary
        if baseline_index < basis_index:
            baseline_fee_0, baseline_fee_1 = 0, 0
        else:
            baseline_principal = self.principal_simulator.simulate_current_principal(
                effective_history=effective_history[:baseline_index + 1],
                states=states[:baseline_index + 1],
                latest_position_tx=latest_position_tx,
                tracked_liquidity_attos=tracked_liquidity_attos,
                basis_type=basis_type,
                basis_opens_current_round=basis_opens_current_round,
                current_round_trade_count_before_basis=current_round_trade_count_before_basis,
            )
            if baseline_principal is None:
                return empty_summary
            baseline_principal_0 = self.value_support.to_attos(
                baseline_principal.get('principal_amount_0_current')
            )
            baseline_principal_1 = self.value_support.to_attos(
                baseline_principal.get('principal_amount_1_current')
            )
            if baseline_principal_0 is None or baseline_principal_1 is None:
                return empty_summary
            baseline_fee_0, baseline_fee_1 = self._position_fee_at_state(
                state=states[baseline_index],
                tracked_liquidity_attos=tracked_liquidity_attos,
                principal_0_attos=baseline_principal_0,
                principal_1_attos=baseline_principal_1,
            )
        return {
            **empty_summary,
            'trailing_24h_fee_amount_0': self._serialize_attos(max(current_fee_0 - baseline_fee_0, 0)),
            'trailing_24h_fee_amount_1': self._serialize_attos(max(current_fee_1 - baseline_fee_1, 0)),
        }

    def _position_fee_at_state(self, *, state, tracked_liquidity_attos, principal_0_attos, principal_1_attos):
        total_supply = self._effective_total_supply_attos(state)
        if total_supply <= 0:
            return 0, 0
        amount_0 = tracked_liquidity_attos * int(state.get('reserve0_after') or 0) // total_supply
        amount_1 = tracked_liquidity_attos * int(state.get('reserve1_after') or 0) // total_supply
        return max(amount_0 - principal_0_attos, 0), max(amount_1 - principal_1_attos, 0)

    def _latest_state_index_before(self, *, exact_states, created_at_ms):
        candidates = [
            index
            for index, state in enumerate(exact_states)
            if int(state.get('created_at') or 0) < created_at_ms
        ]
        return candidates[-1] if candidates else None

    def _state_index_for_transaction(self, *, exact_states, transaction):
        key = (
            int(transaction.get('created_at') or 0),
            int(transaction.get('transaction_id') or 0),
        )
        for index, state in enumerate(exact_states):
            if (int(state.get('created_at') or 0), int(state.get('transaction_id') or 0)) == key:
                return index
        return 0 if exact_states else None

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
        fee_to_history = self._pool_fee_to_history(pool_application_id=pool_application_id)
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
        if not hasattr(self.snapshot_materialization_inputs_repository, 'list_pool_fee_to_history'):
            return {'continuity_case': 'unsupported_source', 'owner': owner}
        history = self._pool_fee_to_history(pool_application_id=pool_application_id)
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

    def _pool_fee_to_account_latest_known(
        self,
        *,
        pool_application_id: str,
    ) -> str | None:
        if not hasattr(self.snapshot_materialization_inputs_repository, 'list_pool_fee_to_history'):
            return None
        history = self._pool_fee_to_history(pool_application_id=pool_application_id)
        if not history:
            return None
        latest = max(
            history,
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
                str(row.get('fee_to_account') or ''),
            ),
        )
        value = latest.get('fee_to_account')
        if value in (None, ''):
            return None
        return str(value)

    def _pool_fee_to_history(
        self,
        *,
        pool_application_id: str,
    ) -> list[dict[str, object]]:
        if not hasattr(self.snapshot_materialization_inputs_repository, 'list_pool_fee_to_history'):
            return []
        history = list(self.snapshot_materialization_inputs_repository.list_pool_fee_to_history(
            pool_application_id=pool_application_id,
        ) or [])
        history.sort(
            key=lambda row: (
                int(row.get('created_at') or 0),
                int(row.get('transaction_id') or 0),
                str(row.get('fee_to_account') or ''),
            )
        )
        return history

    def _public_owner(self, owner: str) -> str:
        return owner
