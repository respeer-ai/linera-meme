from decimal import Decimal

from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult
from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot
from query.read_models.position_metrics_read_result import PositionMetricsReadResult
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
        positions = self.positions_repository.get_positions(owner=owner, status=status)
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
        pool_snapshot = self._pool_state_snapshot(position)
        if pool_snapshot is None:
            return None

        current_total_supply = self._to_decimal(pool_snapshot.current_total_supply())
        fee_free_total_supply = self._to_decimal(pool_snapshot.fee_free_total_supply())
        if (
            current_total_supply is None
            or fee_free_total_supply is None
            or current_total_supply <= Decimal('0')
            or current_total_supply <= fee_free_total_supply
        ):
            return None

        current_reserve_0 = self._to_decimal(pool_snapshot.current_reserve_0())
        current_reserve_1 = self._to_decimal(pool_snapshot.current_reserve_1())
        if current_reserve_0 is None or current_reserve_1 is None:
            return None

        protocol_fee_liquidity = current_total_supply - fee_free_total_supply
        protocol_fee_ratio = protocol_fee_liquidity / current_total_supply
        protocol_fee_amount0 = current_reserve_0 * protocol_fee_ratio
        protocol_fee_amount1 = current_reserve_1 * protocol_fee_ratio
        return {
            'pool_application': position['pool_application'],
            'pool_id': position['pool_id'],
            'token_0': position['token_0'],
            'token_1': position['token_1'],
            'owner': position['owner'],
            'status': position['status'],
            'current_liquidity': position['current_liquidity'],
            'position_liquidity': self._serialize_decimal(protocol_fee_liquidity),
            'current_total_supply': self._serialize_decimal(current_total_supply),
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
            'value_warning_codes': ['virtual_initial_liquidity_protocol_fee_receiver_position'],
            'value_warning_message': (
                'Virtual initial liquidity is pool-level, not owner-held LP. '
                'Protocol yield is projected from parsed pool state.'
            ),
        }

    def _pool_state_snapshot(self, position: dict) -> PositionMetricsPoolStateSnapshot | None:
        if self.virtual_positions_read_model is None:
            return None
        snapshot_inputs_repository = getattr(
            self.virtual_positions_read_model,
            'snapshot_inputs_projection_repository',
            None,
        )
        if snapshot_inputs_repository is None:
            return None
        snapshot_inputs = snapshot_inputs_repository.get_snapshot_inputs(
            owner=position.get('owner'),
            pool_application_id=position.get('pool_application'),
            status='closed',
        )
        if snapshot_inputs is None:
            snapshot_inputs = snapshot_inputs_repository.get_snapshot_inputs(
                owner=position.get('owner'),
                pool_application_id=position.get('pool_application'),
                status='active',
            )
        if snapshot_inputs is None:
            return None
        pool_state_snapshot = snapshot_inputs.pool_state_snapshot()
        if isinstance(pool_state_snapshot, PositionMetricsPoolStateSnapshot):
            return pool_state_snapshot
        return PositionMetricsPoolStateSnapshot(pool_state_snapshot)

    def _to_decimal(self, value: object) -> Decimal | None:
        if value in (None, ''):
            return None
        return Decimal(str(value))

    def _serialize_decimal(self, value: Decimal | None) -> str | None:
        if value is None:
            return None
        if value == 0:
            return '0'
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
