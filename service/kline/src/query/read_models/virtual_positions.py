from decimal import Decimal

from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs


class VirtualPositionsReadModel:
    DISPLAY_AMOUNT_SCALE = Decimal('1000000000000000000')
    SYNTHETIC_VIRTUAL_INITIAL_POSITION_KIND = 'virtual_initial_liquidity'
    SYNTHETIC_PROTOCOL_FEE_RECEIVER_POSITION_KIND = 'virtual_initial_protocol_fee_receiver'

    def __init__(
        self,
        *,
        projection_repository,
        snapshot_inputs_projection_repository,
        pool_catalog_repository=None,
    ):
        self.projection_repository = projection_repository
        self.snapshot_inputs_projection_repository = snapshot_inputs_projection_repository
        self.pool_catalog_repository = pool_catalog_repository

    async def enrich_positions(
        self,
        *,
        owner: str,
        status: str,
        positions: list[dict],
    ) -> list[dict]:
        existing = list(positions)
        existing_keys = {
            (
                str(position.get('pool_application')),
                int(position.get('pool_id')),
                str(position.get('position_kind') or 'recorded'),
            )
            for position in existing
            if position.get('pool_application') is not None and position.get('pool_id') is not None
        }

        candidate_histories = self._load_candidate_histories(owner=owner)
        if candidate_histories is None:
            return existing

        for candidate in candidate_histories:
            snapshot_inputs = self.snapshot_inputs_projection_repository.get_snapshot_inputs(
                owner=owner,
                pool_application_id=candidate['pool_application'],
                status='active',
            )
            if snapshot_inputs is None or self._snapshot_inputs(snapshot_inputs).position_basis_snapshot().raw() is None:
                snapshot_inputs = self.snapshot_inputs_projection_repository.get_snapshot_inputs(
                    owner=owner,
                    pool_application_id=candidate['pool_application'],
                    status='closed',
                )
            if snapshot_inputs is None:
                continue
            snapshot = self._snapshot_inputs(snapshot_inputs)
            pool_state = snapshot.pool_state_snapshot()
            if not pool_state.virtual_initial_liquidity():
                continue

            position_basis = snapshot.position_basis_snapshot()
            synthetic_basis = self._virtual_initial_basis_from_pool_state(pool_state, owner=owner)
            liquidity_value = position_basis.current_liquidity()
            protocol_fee_receiver_account = (
                pool_state.fee_to_account_latest_known()
                or position_basis.fee_to_continuity_owner()
                or synthetic_basis.get('protocol_fee_receiver_account')
            )
            owner_receives_protocol_fees = owner == protocol_fee_receiver_account
            basis_amount_0 = self._string_or_zero(
                position_basis.raw().get('basis_amount_0') if position_basis.raw() else synthetic_basis.get('basis_amount_0')
            )
            basis_amount_1 = self._string_or_zero(
                position_basis.raw().get('basis_amount_1') if position_basis.raw() else synthetic_basis.get('basis_amount_1')
            )
            has_initial_amounts = basis_amount_0 != '0' or basis_amount_1 != '0'

            synthetic_kind = None
            if liquidity_value not in (None, '', '0', '0.', '0.0') or has_initial_amounts:
                synthetic_kind = self.SYNTHETIC_VIRTUAL_INITIAL_POSITION_KIND
                if liquidity_value in (None, ''):
                    liquidity_value = '0'
            elif owner_receives_protocol_fees:
                synthetic_kind = self.SYNTHETIC_PROTOCOL_FEE_RECEIVER_POSITION_KIND
                liquidity_value = '0'
            if synthetic_kind is None:
                continue

            key = (
                str(candidate['pool_application']),
                int(candidate['pool_id']),
                synthetic_kind,
            )
            if key in existing_keys:
                continue

            synthesized = dict(candidate)
            synthesized['status'] = 'virtual'
            synthesized['current_liquidity'] = str(liquidity_value)
            synthesized['added_liquidity'] = str(liquidity_value)
            synthesized['removed_liquidity'] = '0'
            synthesized['add_tx_count'] = max(int(candidate.get('add_tx_count') or 0), 1)
            synthesized['remove_tx_count'] = 0
            synthesized['closed_at'] = None
            synthesized['position_kind'] = synthetic_kind
            synthesized['is_virtual_position'] = True
            synthesized['virtual_initial_amount0'] = basis_amount_0
            synthesized['virtual_initial_amount1'] = basis_amount_1
            synthesized['protocol_fee_receiver_account'] = protocol_fee_receiver_account
            synthesized['protocol_fee_reference_amount0'] = basis_amount_0
            synthesized['protocol_fee_reference_amount1'] = basis_amount_1
            existing.append(synthesized)
            existing_keys.add(key)

        normalized_status = (status or 'active').lower()
        if normalized_status in {'active', 'closed', 'virtual'}:
            existing = [position for position in existing if position.get('status') == normalized_status]
        existing.sort(
            key=lambda row: (
                -(row.get('closed_at') if normalized_status == 'closed' else row.get('updated_at') or 0),
                row.get('pool_id') or 0,
            ),
        )
        return existing

    def _load_candidate_histories(self, *, owner: str) -> list[dict] | None:
        candidate_histories = self.projection_repository.get_owner_candidate_histories(owner=owner)
        if candidate_histories:
            return candidate_histories
        snapshot_rows = self._list_pool_state_snapshots()
        if snapshot_rows is None:
            return candidate_histories
        return [
            candidate
            for candidate in (
                self._candidate_from_pool_state_snapshot(snapshot_row, owner=owner)
                for snapshot_row in snapshot_rows
            )
            if candidate is not None
        ]

    def _candidate_from_pool_state_snapshot(self, snapshot_row: dict, *, owner: str) -> dict | None:
        pool_application = snapshot_row.get('pool_application_id')
        metadata = (snapshot_row.get('state_payload_json') or {}).get('pool_created_metadata') or {}
        catalog_row = self._catalog_pool_by_application().get(str(pool_application))
        token_0 = metadata.get('token_0') or (catalog_row or {}).get('token_0')
        token_1 = metadata.get('token_1') or (catalog_row or {}).get('token_1')
        if pool_application in (None, '') or token_0 in (None, '') or token_1 in (None, ''):
            return None
        return {
            'pool_application': str(pool_application),
            'pool_id': int((catalog_row or {}).get('pool_id') or 0),
            'token_0': str(token_0),
            'token_1': str(token_1) or 'TLINERA',
            'owner': owner,
            'opened_at': None,
            'updated_at': int(snapshot_row.get('last_liquidity_event_time_ms') or snapshot_row.get('last_trade_time_ms') or 0),
            'add_tx_count': 0,
        }

    def _list_pool_state_snapshots(self) -> list[dict] | None:
        projection_repo = getattr(self.snapshot_inputs_projection_repository, 'pool_state_projection_repo', None)
        if projection_repo is None:
            return None
        list_snapshots = getattr(projection_repo, 'list_pool_state_snapshots', None)
        if list_snapshots is None:
            return None
        return list_snapshots()

    def _catalog_pool_by_application(self) -> dict[str, dict]:
        if self.pool_catalog_repository is None:
            return {}
        list_current_pools = getattr(self.pool_catalog_repository, 'list_current_pools', None)
        if list_current_pools is None:
            return {}
        return {
            str(pool['pool_application']): pool
            for pool in (list_current_pools() or [])
            if pool.get('pool_application') not in (None, '')
        }

    def _virtual_initial_basis_from_pool_state(
        self,
        pool_state: PositionMetricsPoolStateSnapshot,
        *,
        owner: str,
    ) -> dict[str, str | None]:
        raw = pool_state.raw() or {}
        basis = (raw.get('state_payload_json') or {}).get('fee_free_basis') or {}
        if not isinstance(basis, dict):
            return {}
        from_account = basis.get('from_account')
        if from_account != owner:
            return {}
        return {
            'basis_amount_0': self._display_string_or_none(basis.get('reserve0_after')),
            'basis_amount_1': self._display_string_or_none(basis.get('reserve1_after')),
            'protocol_fee_receiver_account': str(from_account),
        }

    def _snapshot_inputs(self, snapshot) -> PositionMetricsSnapshotInputs:
        if isinstance(snapshot, PositionMetricsSnapshotInputs):
            return snapshot
        return PositionMetricsSnapshotInputs(snapshot)

    def _pool_state(self, snapshot) -> PositionMetricsPoolStateSnapshot:
        if isinstance(snapshot, PositionMetricsPoolStateSnapshot):
            return snapshot
        return PositionMetricsPoolStateSnapshot(snapshot)

    def _position_basis(self, snapshot) -> PositionMetricsPositionBasisSnapshot:
        if isinstance(snapshot, PositionMetricsPositionBasisSnapshot):
            return snapshot
        return PositionMetricsPositionBasisSnapshot(snapshot)

    def _string_or_zero(self, value: object) -> str:
        if value in (None, ''):
            return '0'
        return str(value)

    def _display_string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        normalized = format((Decimal(str(value)) / self.DISPLAY_AMOUNT_SCALE).normalize(), 'f')
        if '.' in normalized:
            normalized = normalized.rstrip('0').rstrip('.')
        if normalized in {'', '-0'}:
            return '0'
        return normalized
