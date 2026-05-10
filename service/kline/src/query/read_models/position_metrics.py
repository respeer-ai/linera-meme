from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult
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
        if self.virtual_positions_read_model is not None:
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
                        fetch_reason_code='virtual_initial_protocol_fee_receiver',
                    )
                )
                continue
            fetched_result = PositionMetricsFetchedResult.from_fetcher_payload(await self.fetcher(position))
            metric_row = self._build_position_metrics_row(position, fetched_result.live_metrics)
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
        live_metrics: dict,
    ) -> dict:
        normalized_metrics = dict(live_metrics)
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
        return {
            'pool_application': position['pool_application'],
            'pool_id': position['pool_id'],
            'token_0': position['token_0'],
            'token_1': position['token_1'],
            'owner': position['owner'],
            'status': position['status'],
            'current_liquidity': position['current_liquidity'],
            'position_liquidity_live': '0',
            'total_supply_live': None,
            'exact_share_ratio': None,
            'redeemable_amount0': position.get('protocol_fee_reference_amount0', '0'),
            'redeemable_amount1': position.get('protocol_fee_reference_amount1', '0'),
            'virtual_initial_liquidity': True,
            'metrics_status': 'partial_live_redeemable_only',
            'exact_fee_supported': False,
            'exact_principal_supported': False,
            'owner_is_fee_to': True,
            'computation_blockers': [],
            'principal_amount0': '0',
            'principal_amount1': '0',
            'fee_amount0': '0',
            'fee_amount1': '0',
            'protocol_fee_amount0': position.get('protocol_fee_reference_amount0', '0'),
            'protocol_fee_amount1': position.get('protocol_fee_reference_amount1', '0'),
            'value_warning_codes': ['virtual_initial_protocol_fee_receiver_position'],
            'value_warning_message': (
                'Virtual initial liquidity is pool-level, not owner-held LP. '
                'This synthetic position marks the protocol fee receiver and uses the '
                'virtual bootstrap amounts as reference values.'
            ),
        }

    def _is_protocol_fee_receiver_virtual_position(self, position: dict) -> bool:
        return (
            bool(position.get('is_virtual_position'))
            and str(position.get('position_kind') or '')
            == VirtualPositionsReadModel.SYNTHETIC_PROTOCOL_FEE_RECEIVER_POSITION_KIND
        )

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
