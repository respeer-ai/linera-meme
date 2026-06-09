from decimal import Decimal, localcontext

from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult
from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot
from query.read_models.position_metrics_read_result import PositionMetricsReadResult
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs
from query.read_models.virtual_positions import VirtualPositionsReadModel


class PositionMetricsReadModel:
    def __init__(self, positions_repository, fetcher, *, virtual_positions_read_model=None):
        self.positions_repository = positions_repository
        self.fetcher = fetcher
        self.virtual_positions_read_model = virtual_positions_read_model

    async def get_position_metrics(
        self,
        *,
        owner: str,
        status: str,
    ) -> dict:
        repository_status = 'all' if (status or '').lower() == 'virtual' else status
        positions = self.positions_repository.get_positions(owner=owner, status=repository_status)
        if self.virtual_positions_read_model is not None and status in ('all', 'virtual'):
            positions = await self.virtual_positions_read_model.enrich_positions(
                owner=owner,
                status=status,
                positions=positions,
            )
        metrics = []
        metric_diagnostics = []
        shadow_diagnostics = []
        for position in positions:
            if self._is_protocol_fee_receiver_virtual_position(position):
                metric_row = self._build_protocol_fee_receiver_virtual_metrics(position)
                metrics.append(metric_row)
                metric_diagnostics.append(
                    self._build_metric_diagnostic(
                        metric_row=metric_row,
                        fetch_stage='synthetic_virtual_position',
                        fetch_reason_code='virtual_initial_liquidity',
                    )
                )
                continue
            fetched_result = PositionMetricsFetchedResult.from_fetcher_payload(await self.fetcher(position))
            metric_row = self._build_position_metrics_row(position, fetched_result.projected_metrics)
            metrics.append(metric_row)
            metric_diagnostics.append(
                self._build_metric_diagnostic(
                    metric_row=metric_row,
                    fetch_stage=fetched_result.fetch_stage,
                    fetch_reason_code=fetched_result.fetch_reason_code,
                )
            )
            if fetched_result.snapshot_shadow is not None:
                shadow_diagnostics.append(
                    self._build_shadow_diagnostic(
                        diagnostic=fetched_result.snapshot_shadow,
                        fetch_stage=fetched_result.fetch_stage,
                        fetch_reason_code=fetched_result.fetch_reason_code,
                    )
                )
        return PositionMetricsReadResult(
            owner=owner,
            metrics=metrics,
            metric_diagnostics=metric_diagnostics,
            shadow_diagnostics=shadow_diagnostics,
        )

    def _build_position_metrics_row(
        self,
        position: dict,
        projected_metrics: dict,
    ) -> dict:
        normalized_metrics = dict(projected_metrics)
        if 'value_warning_codes' not in normalized_metrics:
            normalized_metrics['value_warning_codes'] = []
        if 'value_warning_message' not in normalized_metrics:
            normalized_metrics['value_warning_message'] = None
        for field_name in (
            'fee_amount0',
            'fee_amount1',
            'protocol_fee_amount0',
            'protocol_fee_amount1',
            'trailing_24h_fee_amount0',
            'trailing_24h_fee_amount1',
        ):
            if normalized_metrics.get(field_name) is None:
                normalized_metrics[field_name] = '0'
        return {
            'pool_application': position['pool_application'],
            'pool_id': position['pool_id'],
            'token_0': position['token_0'],
            'token_1': position['token_1'],
            'owner': position['owner'],
            'status': position['status'],
            'current_liquidity': position['current_liquidity'],
            **normalized_metrics,
        }

    def _build_protocol_fee_receiver_virtual_metrics(self, position: dict) -> dict:
        projected_metrics = self._build_projected_protocol_fee_receiver_virtual_metrics(position)
        if projected_metrics is not None:
            return projected_metrics

        return {
            'pool_application': position['pool_application'],
            'pool_id': position['pool_id'],
            'token_0': position['token_0'],
            'token_1': position['token_1'],
            'owner': position['owner'],
            'status': position['status'],
            'current_liquidity': position['current_liquidity'],
            'position_liquidity': '0',
            'current_total_supply': None,
            'exact_share_ratio': None,
            'redeemable_amount0': position.get('protocol_fee_reference_amount0', '0'),
            'redeemable_amount1': position.get('protocol_fee_reference_amount1', '0'),
            'virtual_initial_liquidity': True,
            'metrics_status': 'partial_projected_redeemable_only',
            'fee_calculation_complete': False,
            'principal_calculation_complete': False,
            'computation_blockers': [],
            'principal_amount0': '0',
            'principal_amount1': '0',
            'fee_amount0': '0',
            'fee_amount1': '0',
            'protocol_fee_amount0': position.get('protocol_fee_reference_amount0', '0'),
            'protocol_fee_amount1': position.get('protocol_fee_reference_amount1', '0'),
            'trailing_24h_fee_amount0': '0',
            'trailing_24h_fee_amount1': '0',
            'trailing_24h_fee_window_start_ms': None,
            'trailing_24h_fee_window_end_ms': None,
            'value_warning_codes': ['virtual_initial_liquidity_protocol_fee_receiver_position'],
            'value_warning_message': (
                'Virtual initial liquidity is pool-level, not owner-held LP. '
                'This synthetic position marks the protocol fee receiver and uses the '
                'virtual bootstrap amounts as reference values.'
            ),
        }

    def _is_protocol_fee_receiver_virtual_position(self, position: dict) -> bool:
        position_kind = str(position.get('position_kind') or '')
        return (
            bool(position.get('is_virtual_position'))
            and self._is_protocol_fee_receiver(position)
            and position_kind == VirtualPositionsReadModel.SYNTHETIC_VIRTUAL_INITIAL_POSITION_KIND
        )

    def _is_protocol_fee_receiver(self, position: dict) -> bool:
        receiver = position.get('protocol_fee_receiver_account')
        return receiver not in (None, '') and str(receiver) == str(position.get('owner'))

    def _build_projected_protocol_fee_receiver_virtual_metrics(self, position: dict) -> dict | None:
        snapshot_inputs = self._metric_snapshot_inputs(position)
        if snapshot_inputs is None:
            return None
        position_basis_snapshot = self._position_basis_snapshot(snapshot_inputs.position_basis_snapshot())
        pool_snapshot = self._pool_state_snapshot_value(snapshot_inputs.pool_state_snapshot())
        if pool_snapshot is None:
            return None

        current_total_supply = self._to_decimal(pool_snapshot.current_total_supply())
        fee_free_total_supply = self._to_decimal(pool_snapshot.fee_free_total_supply())
        if (
            current_total_supply is None
            or fee_free_total_supply is None
            or current_total_supply <= Decimal('0')
        ):
            return None

        current_reserve_0 = self._to_decimal(pool_snapshot.current_reserve_0())
        current_reserve_1 = self._to_decimal(pool_snapshot.current_reserve_1())
        if current_reserve_0 is None or current_reserve_1 is None:
            return None

        minted_fee = self._owner_protocol_fee_liquidity(
            position=position,
            position_basis_snapshot=position_basis_snapshot,
            current_total_supply=current_total_supply,
            fee_free_total_supply=fee_free_total_supply,
        )
        pending_fee = self._pending_protocol_fee_liquidity(pool_snapshot)
        protocol_fee_liquidity = (minted_fee or Decimal('0')) + pending_fee
        if protocol_fee_liquidity <= Decimal('0'):
            return None

        effective_total_supply = current_total_supply + pending_fee
        protocol_fee_ratio = protocol_fee_liquidity / effective_total_supply
        protocol_fee_amount0 = current_reserve_0 * protocol_fee_ratio
        protocol_fee_amount1 = current_reserve_1 * protocol_fee_ratio
        trailing_fee_amount0 = position_basis_snapshot.trailing_24h_fee_amount_0() or '0'
        trailing_fee_amount1 = position_basis_snapshot.trailing_24h_fee_amount_1() or '0'
        return {
            'pool_application': position['pool_application'],
            'pool_id': position['pool_id'],
            'token_0': position['token_0'],
            'token_1': position['token_1'],
            'owner': position['owner'],
            'status': position['status'],
            'current_liquidity': position['current_liquidity'],
            'position_liquidity': self._serialize_decimal(protocol_fee_liquidity),
            'current_total_supply': self._serialize_decimal(effective_total_supply),
            'exact_share_ratio': self._serialize_decimal(protocol_fee_ratio),
            'redeemable_amount0': self._serialize_decimal(protocol_fee_amount0),
            'redeemable_amount1': self._serialize_decimal(protocol_fee_amount1),
            'virtual_initial_liquidity': True,
            'metrics_status': 'projection_protocol_fee_receiver_virtual',
            'fee_calculation_complete': True,
            'principal_calculation_complete': False,
            'computation_blockers': [],
            'principal_amount0': '0',
            'principal_amount1': '0',
            'fee_amount0': '0',
            'fee_amount1': '0',
            'protocol_fee_amount0': self._serialize_decimal(protocol_fee_amount0),
            'protocol_fee_amount1': self._serialize_decimal(protocol_fee_amount1),
            'trailing_24h_fee_amount0': trailing_fee_amount0,
            'trailing_24h_fee_amount1': trailing_fee_amount1,
            'trailing_24h_fee_window_start_ms': position_basis_snapshot.trailing_24h_fee_window_start_ms(),
            'trailing_24h_fee_window_end_ms': position_basis_snapshot.trailing_24h_fee_window_end_ms(),
            'value_warning_codes': ['virtual_initial_liquidity_protocol_fee_receiver_position'],
            'value_warning_message': (
                'Virtual initial liquidity is pool-level, not owner-held LP. '
                'Protocol yield is projected from parsed pool state.'
            ),
        }

    def _pending_protocol_fee_liquidity(self, pool_snapshot) -> Decimal:
        fee_free_reserve_0 = self._to_decimal(pool_snapshot.fee_free_reserve_0())
        fee_free_reserve_1 = self._to_decimal(pool_snapshot.fee_free_reserve_1())
        current_reserve_0 = self._to_decimal(pool_snapshot.current_reserve_0())
        current_reserve_1 = self._to_decimal(pool_snapshot.current_reserve_1())
        if (
            fee_free_reserve_0 is None
            or fee_free_reserve_1 is None
            or current_reserve_0 is None
            or current_reserve_1 is None
        ):
            return Decimal('0')
        fee_free_k2 = fee_free_reserve_0 * fee_free_reserve_1
        current_k2 = current_reserve_0 * current_reserve_1
        if fee_free_k2 <= Decimal('0') or current_k2 <= fee_free_k2:
            return Decimal('0')
        fee_free_k = fee_free_k2.sqrt()
        current_k = current_k2.sqrt()
        if current_k <= fee_free_k:
            return Decimal('0')
        fee_free_total_supply = self._to_decimal(pool_snapshot.fee_free_total_supply())
        if fee_free_total_supply is None or fee_free_total_supply <= Decimal('0'):
            return Decimal('0')
        denominator = current_k * Decimal('5') + fee_free_k
        if denominator <= Decimal('0'):
            return Decimal('0')
        return fee_free_total_supply * (current_k - fee_free_k) / denominator

    def _position_basis_snapshot(self, snapshot) -> PositionMetricsPositionBasisSnapshot:
        if isinstance(snapshot, PositionMetricsPositionBasisSnapshot):
            return snapshot
        return PositionMetricsPositionBasisSnapshot(snapshot)

    def _pool_state_snapshot_value(self, snapshot) -> PositionMetricsPoolStateSnapshot:
        if isinstance(snapshot, PositionMetricsPoolStateSnapshot):
            return snapshot
        return PositionMetricsPoolStateSnapshot(snapshot)

    def _owner_protocol_fee_liquidity(
        self,
        *,
        position: dict,
        position_basis_snapshot,
        current_total_supply: Decimal,
        fee_free_total_supply: Decimal,
    ) -> Decimal | None:
        materialized = self._materialized_owner_protocol_fee_liquidity(position_basis_snapshot)
        if materialized is None or materialized <= Decimal('0'):
            return None
        return materialized

    def _materialized_owner_protocol_fee_liquidity(self, position_basis_snapshot) -> Decimal | None:
        if position_basis_snapshot is None:
            return None
        if not isinstance(position_basis_snapshot, PositionMetricsPositionBasisSnapshot):
            position_basis_snapshot = PositionMetricsPositionBasisSnapshot(position_basis_snapshot)
        value = self._to_decimal(position_basis_snapshot.full_protocol_fee_liquidity_owned_by_current_owner())
        if value is None or value <= Decimal('0'):
            return None
        return value

    def _owner_receives_pending_protocol_fees(self, *, position: dict, position_basis_snapshot) -> bool:
        owner = str(position.get('owner') or '')
        if not owner:
            return False
        if position_basis_snapshot is None:
            return False
        if not isinstance(position_basis_snapshot, PositionMetricsPositionBasisSnapshot):
            position_basis_snapshot = PositionMetricsPositionBasisSnapshot(position_basis_snapshot)
        latest_fee_to = position_basis_snapshot.fee_to_account_latest_known()
        if latest_fee_to not in (None, ''):
            return str(latest_fee_to) == owner
        continuity_owner = position_basis_snapshot.fee_to_continuity_owner()
        if continuity_owner not in (None, ''):
            return str(continuity_owner) == owner
        return False

    def _snapshot_inputs(self, snapshot) -> PositionMetricsSnapshotInputs:
        if isinstance(snapshot, PositionMetricsSnapshotInputs):
            return snapshot
        if hasattr(snapshot, 'position_basis_snapshot') and hasattr(snapshot, 'pool_state_snapshot'):
            return PositionMetricsSnapshotInputs({
                'position_basis_snapshot': snapshot.position_basis_snapshot(),
                'pool_state_snapshot': snapshot.pool_state_snapshot(),
            })
        return PositionMetricsSnapshotInputs(snapshot)

    def _metric_snapshot_inputs(self, position: dict) -> PositionMetricsSnapshotInputs | None:
        if self.virtual_positions_read_model is None:
            return None
        snapshot_inputs_repository = getattr(
            self.virtual_positions_read_model,
            'snapshot_inputs_projection_repository',
            None,
        )
        if snapshot_inputs_repository is None:
            return None
        active_snapshot = snapshot_inputs_repository.get_snapshot_inputs(
            owner=position.get('owner'),
            pool_application_id=position.get('pool_application'),
            status='active',
        )
        if active_snapshot is not None:
            active = self._snapshot_inputs(active_snapshot)
            if active.position_basis_snapshot().raw() is not None:
                return active
        closed_snapshot = snapshot_inputs_repository.get_snapshot_inputs(
            owner=position.get('owner'),
            pool_application_id=position.get('pool_application'),
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

    def _to_decimal(self, value: object) -> Decimal | None:
        if value in (None, ''):
            return None
        return Decimal(str(value))

    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        if value == 0:
            return '0'
        with localcontext() as context:
            context.prec = max(60, len(value.as_tuple().digits) + 18)
            return format(value.quantize(Decimal('0.000000000000000001')).normalize(), 'f')

    def _build_metric_diagnostic(
        self,
        *,
        metric_row: dict,
        fetch_stage: str | None,
        fetch_reason_code: str | None,
    ) -> dict:
        diagnostic = dict(metric_row)
        diagnostic['fetch_stage'] = fetch_stage
        diagnostic['fetch_reason_code'] = fetch_reason_code
        return diagnostic

    def _build_shadow_diagnostic(
        self,
        *,
        diagnostic: dict,
        fetch_stage: str | None,
        fetch_reason_code: str | None,
    ) -> dict:
        normalized_diagnostic = dict(diagnostic)
        normalized_diagnostic['fetch_stage'] = fetch_stage
        normalized_diagnostic['fetch_reason_code'] = fetch_reason_code
        return normalized_diagnostic
