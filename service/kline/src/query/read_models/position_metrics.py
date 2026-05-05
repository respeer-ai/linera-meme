from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult
from query.read_models.position_metrics_read_result import PositionMetricsReadResult


class PositionMetricsReadModel:
    def __init__(self, positions_repository, fetcher):
        self.positions_repository = positions_repository
        self.fetcher = fetcher

    async def get_position_metrics(
        self,
        *,
        owner: str,
        status: str,
    ) -> dict:
        positions = self.positions_repository.get_positions(owner=owner, status=status)
        metrics = []
        metric_diagnostics = []
        shadow_diagnostics = []
        for position in positions:
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
