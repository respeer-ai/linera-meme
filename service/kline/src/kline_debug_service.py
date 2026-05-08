from kline_observability_debug_service import KlineObservabilityDebugService
from kline_position_metrics_debug_service import KlinePositionMetricsDebugService


class KlineDebugService:
    def __init__(
        self,
        *,
        runtime,
        position_metrics_public_api,
        position_metrics_dependencies_factory,
        observability_facade,
    ):
        self._position_metrics = KlinePositionMetricsDebugService(
            runtime=runtime,
            position_metrics_public_api=position_metrics_public_api,
            position_metrics_dependencies_factory=position_metrics_dependencies_factory,
        )
        self._observability = KlineObservabilityDebugService(
            observability_facade=observability_facade,
        )

    async def build_position_metrics_readiness_debug_payload(
        self,
        *,
        owner: str,
        status: str,
        sample_limit: int,
    ):
        return await self._position_metrics.build_position_metrics_readiness_debug_payload(
            owner=owner,
            status=status,
            sample_limit=sample_limit,
        )

    def get_replay_transaction_audit(
        self,
        *,
        pool_id: int,
        pool_application: str,
        virtual_initial_liquidity: bool,
        start_id: int | None,
        end_id: int | None,
        swap_out_tolerance_attos: int,
    ):
        return self._position_metrics.get_replay_transaction_audit(
            pool_id=pool_id,
            pool_application=pool_application,
            virtual_initial_liquidity=virtual_initial_liquidity,
            start_id=start_id,
            end_id=end_id,
            swap_out_tolerance_attos=swap_out_tolerance_attos,
        )

    def get_diagnostics(
        self,
        *,
        source: str | None,
        owner: str | None,
        pool_application: str | None,
        pool_id: int | None,
        limit: int,
    ):
        return self._position_metrics.get_diagnostics(
            source=source,
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
            limit=limit,
        )

    def get_debug_traces(
        self,
        *,
        source: str | None,
        component: str | None,
        operation: str | None,
        owner: str | None,
        pool_application: str | None,
        pool_id: int | None,
        start_at: int | None,
        end_at: int | None,
        limit: int,
    ):
        return self._position_metrics.get_debug_traces(
            source=source,
            component=component,
            operation=operation,
            owner=owner,
            pool_application=pool_application,
            pool_id=pool_id,
            start_at=start_at,
            end_at=end_at,
            limit=limit,
        )

    def get_debug_pool_bundle(
        self,
        *,
        pool_application: str,
        pool_id: int,
        owner: str | None,
        transaction_limit: int,
        diagnostics_limit: int,
    ):
        return self._position_metrics.get_debug_pool_bundle(
            pool_application=pool_application,
            pool_id=pool_id,
            owner=owner,
            transaction_limit=transaction_limit,
            diagnostics_limit=diagnostics_limit,
        )

    async def run_catch_up(self, *, chain_id: str | None, max_blocks: int | None):
        return await self._observability.run_catch_up(
            chain_id=chain_id,
            max_blocks=max_blocks,
        )

    async def run_normalization_replay(
        self,
        *,
        raw_table: str | None,
        batch_limit: int | None,
        after_sequence: int | None = None,
        ignore_cursor: bool = False,
        max_batches: int | None,
        reprocess_reason: str | None,
    ):
        return await self._observability.run_normalization_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            after_sequence=after_sequence,
            ignore_cursor=ignore_cursor,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )

    async def run_market_derivation_replay(
        self,
        *,
        raw_table: str | None,
        batch_limit: int | None,
        after_sequence: int | None = None,
        ignore_cursor: bool = False,
        max_batches: int | None,
        reprocess_reason: str | None,
    ):
        return await self._observability.run_market_derivation_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            after_sequence=after_sequence,
            ignore_cursor=ignore_cursor,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )

    def get_debug_observability(
        self,
        *,
        chain_ids: str | None,
        run_statuses: str | None,
        anomaly_statuses: str | None,
        limit: int,
    ):
        return self._observability.get_debug_observability(
            chain_ids=chain_ids,
            run_statuses=run_statuses,
            anomaly_statuses=anomaly_statuses,
            limit=limit,
        )

    async def recover_observability(self):
        return await self._observability.recover_observability()
