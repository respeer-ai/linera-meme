import json


class PositionMetricsSnapshotMaterializer:
    def __init__(
        self,
        *,
        snapshot_builder,
        position_state_snapshot_repository,
        pool_state_snapshot_repository,
    ):
        self.snapshot_builder = snapshot_builder
        self.position_state_snapshot_repository = position_state_snapshot_repository
        self.pool_state_snapshot_repository = pool_state_snapshot_repository


    def repair_position_state_gaps(
        self,
        *,
        settled_liquidity_change_repository,
        settled_output_batch_factory,
        batch_limit: int = 500,
        max_batches: int = 20,
    ) -> dict[str, object]:
        total_outputs = 0
        total_positions = 0
        batches = 0
        for _ in range(max(0, int(max_batches))):
            outputs = settled_liquidity_change_repository.list_position_snapshot_gap_changes(
                limit=batch_limit,
            )
            if not outputs:
                break
            batches += 1
            total_outputs += len(outputs)
            summary = self.materialize_output_batch(
                settled_output_batch_factory.build(outputs),
                update_pool_states=False,
            )
            if summary.get('degraded'):
                return {
                    'degraded': True,
                    'error_text': summary.get('error_text'),
                    'batches': batches,
                    'repaired_output_count': total_outputs,
                    'repaired_position_count': total_positions,
                }
            total_positions += int(summary.get('persisted_position_state_count') or 0)
            if len(outputs) < int(batch_limit):
                break
        return {
            'degraded': False,
            'batches': batches,
            'repaired_output_count': total_outputs,
            'repaired_position_count': total_positions,
        }

    def materialize_output_batch(
        self,
        output_batch,
        *,
        update_pool_states: bool = True,
    ) -> dict[str, object]:
        if not output_batch.outputs:
            return self._summary()
        try:
            pool_states = (
                self._build_pool_states_incremental(output_batch)
                if update_pool_states
                else []
            )
            position_replacements = self._build_position_states_incremental(output_batch)
            for replacement in position_replacements:
                self.position_state_snapshot_repository.replace_position_states(
                    owner=replacement['owner'],
                    pool_application_id=replacement['pool_application_id'],
                    states=replacement['states'],
                )
            if pool_states:
                self.pool_state_snapshot_repository.upsert_pool_states(pool_states)
            return self._summary(
                affected_pool_count=len(pool_states),
                affected_position_count=len(position_replacements),
                persisted_pool_state_count=len(pool_states),
                persisted_position_state_count=sum(
                    len(replacement['states'])
                    for replacement in position_replacements
                ),
                degraded=False,
            )
        except Exception as error:
            return self._summary(
                degraded=True,
                error_text=str(error),
            )

    def _build_pool_states_incremental(self, output_batch):
        pool_states = []
        for pool_application_id, pool_chain_id in output_batch.affected_pools():
            row = self.pool_state_snapshot_repository.get_pool_state(
                pool_application_id=pool_application_id,
            )
            state = self._pool_state_attos_from_row(row)
            events = [
                o for o in output_batch.outputs
                if str(o.get('pool_application_id')) == pool_application_id
            ]
            events.sort(key=lambda o: (
                int(o.get('created_at') or o.get('event_time_ms') or o.get('trade_time_ms') or 0),
                int(o.get('transaction_id') or 0),
            ))
            for event in events:
                tx_id = int(event.get('transaction_id') or 0)
                if tx_id <= state.get('last_transaction_id', 0):
                    continue
                state = self.snapshot_builder.apply_pool_state(state, event)
            pool_states.append(
                self._pool_state_row_from_attos(state, pool_application_id, pool_chain_id)
            )
        return pool_states

    def _pool_state_attos_from_row(self, row):
        vs = self.snapshot_builder.value_support
        if row is None:
            return {
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
        return {
            'reserve0': vs.to_attos(row.get('current_reserve_0')) or 0,
            'reserve1': vs.to_attos(row.get('current_reserve_1')) or 0,
            'total_supply': vs.to_attos(row.get('current_total_supply')) or 0,
            'k_last': vs.to_attos(row.get('current_k_last')) or 0,
            'pending_protocol_fee': vs.to_attos(row.get('pending_protocol_fee')) or 0,
            'total_minted_protocol_fee': vs.to_attos(row.get('total_minted_protocol_fee')) or 0,
            'swap_count': int(row.get('swap_count') or 0),
            'last_trade_time_ms': int(row.get('last_trade_time_ms') or 0),
            'last_liquidity_event_time_ms': int(row.get('last_liquidity_event_time_ms') or 0),
            'last_transaction_id': int(row.get('last_transaction_id') or 0),
            'fee_free_basis_transaction_id': row.get('fee_free_basis_transaction_id'),
            'fee_free_basis_time_ms': row.get('fee_free_basis_time_ms'),
            'fee_free_reserve0': vs.to_attos(row.get('fee_free_reserve_0')) or 0,
            'fee_free_reserve1': vs.to_attos(row.get('fee_free_reserve_1')) or 0,
            'fee_free_total_supply': vs.to_attos(row.get('fee_free_total_supply')) or 0,
        }

    def _pool_state_row_from_attos(self, state, pool_application_id, pool_chain_id):
        b = self.snapshot_builder
        tx_id = state.get('last_transaction_id')
        source_key = (
            f'{pool_application_id}:'
            f'{tx_id or state.get("last_trade_time_ms") or "snapshot"}'
        )
        return {
            'pool_state_id': pool_application_id,
            'pool_application_id': pool_application_id,
            'pool_chain_id': pool_chain_id,
            'last_trade_time_ms': state.get('last_trade_time_ms'),
            'last_liquidity_event_time_ms': state.get('last_liquidity_event_time_ms'),
            'last_transaction_id': tx_id,
            'swap_count': state.get('swap_count', 0),
            'current_reserve_0': b._serialize_attos(state['reserve0']),
            'current_reserve_1': b._serialize_attos(state['reserve1']),
            'current_total_supply': b._serialize_attos(state['total_supply']),
            'current_k_last': b._serialize_attos(state['k_last']),
            'total_minted_protocol_fee': b._serialize_attos(
                state.get('total_minted_protocol_fee', 0)
            ),
            'pending_protocol_fee': b._serialize_attos(
                state.get('pending_protocol_fee', 0)
            ),
            'fee_free_basis_transaction_id': state.get('fee_free_basis_transaction_id'),
            'fee_free_basis_time_ms': state.get('fee_free_basis_time_ms'),
            'fee_free_reserve_0': b._serialize_attos(state.get('fee_free_reserve0', 0)),
            'fee_free_reserve_1': b._serialize_attos(state.get('fee_free_reserve1', 0)),
            'fee_free_total_supply': b._serialize_attos(state.get('fee_free_total_supply', 0)),
            'source_event_key': source_key,
            'state_payload_json': {},
        }

    def _build_position_states_incremental(self, output_batch):
        positions = {}
        for output in output_batch.liquidity_changes():
            if not self._is_position_liquidity(output):
                continue
            owner = str(output['owner'])
            pool_app_id = str(output['pool_application_id'])
            key = (owner, pool_app_id)
            if key not in positions:
                row = self.position_state_snapshot_repository.get_position_state(
                    owner=owner,
                    pool_application_id=pool_app_id,
                )
                positions[key] = {
                    'owner': owner,
                    'pool_application_id': pool_app_id,
                    'pool_chain_id': output.get('pool_chain_id'),
                    'state': self._position_state_attos_from_row(row),
                }
            tx_id = int(output.get('transaction_id') or 0)
            if tx_id <= positions[key]['state'].get('last_transaction_id', 0):
                continue
            if self._is_over_remove(positions[key]['state'], output):
                positions[key]['state'] = self._record_skipped_position_remove(
                    positions[key]['state'], output,
                )
                continue
            positions[key]['state'] = (
                self.snapshot_builder.apply_position_state(
                    positions[key]['state'], output,
                )
            )
        return [
            {
                'owner': p['owner'],
                'pool_application_id': p['pool_application_id'],
                'states': [
                    self._position_state_row_from_attos(
                        p['state'], p['owner'], p['pool_application_id'],
                        p['pool_chain_id'],
                    ),
                ],
            }
            for p in positions.values()
        ]

    def _is_position_liquidity(self, output) -> bool:
        return bool(output.get('is_position_liquidity', True))

    def _is_over_remove(self, state, output) -> bool:
        if self.snapshot_builder._liquidity_transaction_type(output) != 'RemoveLiquidity':
            return False
        liquidity = self.snapshot_builder._liquidity_attos(output)
        current = int(state.get('running_liquidity') or 0)
        return current <= 0 or liquidity - current > self._position_epsilon_attos()

    def _record_skipped_position_remove(self, state, output):
        state = dict(state)
        tx_id = int(output.get('transaction_id') or 0)
        skipped = list(state.get('skipped_position_removes') or [])
        skipped.append({
            'transaction_id': tx_id,
            'liquidity': self.snapshot_builder._serialize_attos(
                self.snapshot_builder._liquidity_attos(output)
            ),
            'reason': 'over_removed_position_liquidity',
            'liquidity_semantics': output.get('liquidity_semantics'),
        })
        state['skipped_position_removes'] = skipped[-10:]
        state['last_transaction_id'] = max(state.get('last_transaction_id', 0), tx_id)
        return state

    def _position_epsilon_attos(self) -> int:
        value_support = self.snapshot_builder.value_support
        epsilon = getattr(value_support, 'epsilon', None)
        if epsilon is None:
            return 0
        return value_support.to_attos(epsilon) or 0

    def _decode_json_object(self, value):
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value:
            try:
                decoded = json.loads(value)
            except json.JSONDecodeError:
                return {}
            if isinstance(decoded, dict):
                return decoded
        return {}

    def _position_state_attos_from_row(self, row):
        vs = self.snapshot_builder.value_support
        if row is None:
            return {
                'running_liquidity': 0, 'current_liquidity': 0,
                'added_liquidity': 0, 'removed_liquidity': 0,
                'status': None,
                'basis_type': None,
                'basis_amount_0': '0',
                'basis_amount_1': '0',
                'basis_time_ms': None,
                'basis_transaction_id': None,
                'current_round_liquidity_event_count': 0,
                'current_round_started_at': None,
                'current_round_started_transaction_id': None,
                'last_transaction_id': 0,
            }
        payload = self._decode_json_object(row.get('state_payload_json'))
        return {
            'running_liquidity': vs.to_attos(row.get('current_liquidity')) or 0,
            'current_liquidity': vs.to_attos(row.get('current_liquidity')) or 0,
            'added_liquidity': vs.to_attos(payload.get('added_liquidity')) or 0,
            'removed_liquidity': vs.to_attos(payload.get('removed_liquidity')) or 0,
            'status': row.get('status'),
            'basis_type': row.get('basis_type'),
            'basis_amount_0': row.get('basis_amount_0', '0'),
            'basis_amount_1': row.get('basis_amount_1', '0'),
            'basis_time_ms': row.get('basis_time_ms'),
            'basis_transaction_id': row.get('basis_transaction_id'),
            'current_round_liquidity_event_count': int(
                payload.get('current_round_liquidity_event_count') or 0
            ),
            'current_round_started_at': payload.get('current_round_started_at'),
            'current_round_started_transaction_id': (
                payload.get('current_round_started_transaction_id')
            ),
            'last_transaction_id': int(payload.get('last_transaction_id') or 0),
            'skipped_position_removes': list(
                payload.get('skipped_position_removes') or []
            ),
        }

    def _position_state_row_from_attos(
        self, state, owner, pool_app_id, pool_chain_id,
    ):
        b = self.snapshot_builder
        status = state.get('status') or 'active'
        liquidity = state.get('current_liquidity', 0)
        return {
            'position_state_id': f'{owner}:{pool_app_id}:{status}',
            'owner': owner,
            'pool_application_id': pool_app_id,
            'pool_chain_id': pool_chain_id,
            'status': status,
            'basis_type': state.get('basis_type'),
            'current_liquidity': b._serialize_attos(liquidity),
            'basis_liquidity': b._serialize_attos(liquidity),
            'basis_amount_0': state.get('basis_amount_0', '0'),
            'basis_amount_1': state.get('basis_amount_1', '0'),
            'basis_time_ms': state.get('basis_time_ms'),
            'basis_transaction_id': state.get('basis_transaction_id'),
            'source_event_key': (
                f'{owner}:{pool_app_id}:'
                f'{state.get("basis_transaction_id") or "snapshot"}'
            ),
            'state_payload_json': {
                'added_liquidity': b._serialize_attos(
                    state.get('added_liquidity', 0)
                ),
                'removed_liquidity': b._serialize_attos(
                    state.get('removed_liquidity', 0)
                ),
                'prior_liquidity_before_basis': '0',
                'basis_opens_current_round': True,
                'has_only_zero_liquidity_before_basis': True,
                'current_round_liquidity_event_count': (
                    state.get('current_round_liquidity_event_count', 0)
                ),
                'current_round_started_at': state.get('current_round_started_at'),
                'current_round_started_transaction_id': (
                    state.get('current_round_started_transaction_id')
                ),
                'last_transaction_id': state.get('last_transaction_id', 0),
                'current_round_trade_count_before_basis': 0,
                'trade_count_between_basis_and_fee_free_basis': 0,
                'latest_liquidity_transaction': {},
                'exact_current_principal': {},
                'fee_to_continuity': {},
                'skipped_position_removes': state.get('skipped_position_removes') or [],
            },
        }

    def bootstrap_pool_state(self, pool_application_id, pool_chain_id=None):
        pool_state = self.snapshot_builder._build_pool_state(
            pool_application_id=pool_application_id,
            pool_chain_id=pool_chain_id,
        )
        if pool_state is not None:
            self.pool_state_snapshot_repository.upsert_pool_states([pool_state])
        return pool_state

    def replay_pool_state(self, pool_application_id, pool_chain_id=None):
        return self.snapshot_builder._build_pool_state(
            pool_application_id=pool_application_id,
            pool_chain_id=pool_chain_id,
        )

    def _summary(
        self,
        *,
        affected_pool_count: int = 0,
        affected_position_count: int = 0,
        persisted_pool_state_count: int = 0,
        persisted_position_state_count: int = 0,
        degraded: bool = False,
        error_text: str | None = None,
    ) -> dict[str, object]:
        return {
            'affected_pool_count': affected_pool_count,
            'affected_position_count': affected_position_count,
            'persisted_pool_state_count': persisted_pool_state_count,
            'persisted_position_state_count': persisted_position_state_count,
            'degraded': degraded,
            'error_text': error_text,
        }
