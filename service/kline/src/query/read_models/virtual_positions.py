from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs


class VirtualPositionsReadModel:
    SYNTHETIC_VIRTUAL_INITIAL_POSITION_KIND = 'virtual_initial_liquidity'

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
            if not self._candidate_has_virtual_initial_liquidity(candidate):
                continue
            snapshot = self._load_metric_enrichment_snapshot(
                owner=owner,
                pool_application=candidate['pool_application'],
            )
            pool_state = snapshot.pool_state_snapshot() if snapshot is not None else self._pool_state({})
            position_basis = snapshot.position_basis_snapshot() if snapshot is not None else self._position_basis({})

            liquidity_value = self._string_or_zero(
                position_basis.current_liquidity()
                or candidate.get('virtual_initial_liquidity')
            )
            protocol_fee_receiver_account = (
                pool_state.fee_to_account_latest_known()
                or position_basis.fee_to_continuity_owner()
                or candidate.get('protocol_fee_receiver_account')
            )
            basis_amount_0 = self._string_or_zero(
                (
                    position_basis.raw().get('basis_amount_0')
                    if position_basis.raw()
                    else candidate.get('virtual_initial_amount0')
                )
            )
            basis_amount_1 = self._string_or_zero(
                (
                    position_basis.raw().get('basis_amount_1')
                    if position_basis.raw()
                    else candidate.get('virtual_initial_amount1')
                )
            )

            key = (
                str(candidate['pool_application']),
                int(candidate['pool_id']),
                self.SYNTHETIC_VIRTUAL_INITIAL_POSITION_KIND,
            )
            if key in existing_keys:
                continue

            synthesized = dict(candidate)
            synthesized['status'] = 'virtual'
            synthesized['current_liquidity'] = liquidity_value
            synthesized['added_liquidity'] = liquidity_value
            synthesized['removed_liquidity'] = '0'
            synthesized['add_tx_count'] = max(int(candidate.get('add_tx_count') or 0), 1)
            synthesized['remove_tx_count'] = 0
            synthesized['closed_at'] = None
            synthesized['position_kind'] = self.SYNTHETIC_VIRTUAL_INITIAL_POSITION_KIND
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

    def _load_metric_enrichment_snapshot(
        self,
        *,
        owner: str,
        pool_application: str,
    ) -> PositionMetricsSnapshotInputs | None:
        active_snapshot = self.snapshot_inputs_projection_repository.get_snapshot_inputs(
            owner=owner,
            pool_application_id=pool_application,
            status='active',
        )
        if active_snapshot is not None:
            active = self._snapshot_inputs(active_snapshot)
            if active.position_basis_snapshot().raw() is not None:
                return active
        closed_snapshot = self.snapshot_inputs_projection_repository.get_snapshot_inputs(
            owner=owner,
            pool_application_id=pool_application,
            status='closed',
        )
        if closed_snapshot is not None:
            closed = self._snapshot_inputs(closed_snapshot)
            if closed.position_basis_snapshot().raw() is not None:
                return closed
            if closed.pool_state_snapshot().raw() is not None:
                return closed
        if active_snapshot is not None and active.pool_state_snapshot().raw() is not None:
            return active
        return None

    def _load_candidate_histories(self, *, owner: str) -> list[dict] | None:
        return self.projection_repository.get_owner_candidate_histories(owner=owner)

    def _candidate_has_virtual_initial_liquidity(self, candidate: dict) -> bool:
        return (
            candidate.get('virtual_initial_amount0') is not None
            or candidate.get('virtual_initial_amount1') is not None
            or candidate.get('virtual_initial_liquidity') is not None
        )

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

