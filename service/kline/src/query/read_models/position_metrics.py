class PositionMetricsReadModel:
    def __init__(self, repository, fetcher):
        self.repository = repository
        self.fetcher = fetcher

    async def get_position_metrics(
        self,
        *,
        owner: str,
        status: str,
    ) -> dict:
        positions = self.repository.get_positions(owner=owner, status=status)
        metrics = []
        shadow_diagnostics = []
        for position in positions:
            fetched = await self.fetcher(position)
            live_metrics, shadow_snapshot = self._unpack_fetch_result(fetched)
            metrics.append(self._build_position_metrics_row(position, live_metrics))
            if shadow_snapshot is not None:
                shadow_diagnostics.append(shadow_snapshot)
        payload = {
            'owner': owner,
            'metrics': metrics,
        }
        if shadow_diagnostics:
            payload['_shadow_diagnostics'] = shadow_diagnostics
        return payload

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

    def _unpack_fetch_result(
        self,
        fetched,
    ) -> tuple[dict, dict | None]:
        if not isinstance(fetched, dict):
            return fetched, None
        if 'live_metrics' not in fetched:
            return fetched, None
        return fetched['live_metrics'], fetched.get('snapshot_shadow')
