import asyncio

from app.observability_status import ObservabilityStatus


class ObservabilitySupervisor:
    def __init__(self, runtime):
        self.runtime = runtime
        self.status = ObservabilityStatus(configured=runtime is not None)
        self._lock = asyncio.Lock()
        self._start_task = None

    def start_in_background(self):
        if self.runtime is None:
            self.status.mark_disabled('observability is not configured')
            return None
        if self._start_task is not None and not self._start_task.done():
            return self._start_task
        self._start_task = asyncio.create_task(self.start_if_configured())
        return self._start_task

    async def start_if_configured(self) -> bool:
        if self.runtime is None:
            self.status.mark_disabled('observability is not configured')
            return False
        async with self._lock:
            if self.runtime.is_started():
                self.status.mark_ready()
                return True
            self.status.mark_starting()
            try:
                stage_results = await self.runtime.start() or {}
            except Exception as error:
                self.status.mark_degraded(error)
                return False
            self._apply_stage_results(stage_results)
            if any(result.get('status') == 'degraded' for result in stage_results.values()):
                self.status.mark_degraded('observability startup completed with degraded stages')
                return False
            self.status.mark_ready()
            return True

    async def recover(self) -> bool:
        if self.runtime is None:
            self.status.mark_disabled('observability is not configured')
            return False
        async with self._lock:
            if not self.runtime.is_started():
                return await self.start_if_configured()
            try:
                stage_results = await self.runtime.refresh() or {}
            except Exception as error:
                self.status.mark_degraded(error)
                return False
            self._apply_stage_results(stage_results)
            if any(result.get('status') == 'degraded' for result in stage_results.values()):
                self.status.mark_degraded('observability refresh completed with degraded stages')
                return False
            self.status.mark_ready()
            return True

    async def shutdown(self) -> None:
        if self._start_task is not None:
            await asyncio.gather(self._start_task, return_exceptions=True)
            self._start_task = None
        if self.runtime is None:
            self.status.mark_disabled('observability is not configured')
            return
        async with self._lock:
            try:
                await self.runtime.shutdown()
            except Exception as error:
                self.status.mark_degraded(error)
                return
            self.status.mark_stopped()

    async def run_catch_up(self, *, chain_id: str | None, max_blocks: int | None) -> dict[str, object]:
        if not self.has_started_runtime():
            raise RuntimeError('Observability runtime is not ready')
        try:
            return await self.runtime.run_catch_up(chain_id=chain_id, max_blocks=max_blocks)
        except Exception as error:
            self.status.mark_degraded(error)
            raise

    async def run_normalization_replay(
        self,
        *,
        raw_table: str | None,
        batch_limit: int | None,
        after_sequence: int | None = None,
        ignore_cursor: bool = False,
        max_batches: int | None,
        reprocess_reason: str | None,
    ) -> dict[str, object]:
        if not self.has_started_runtime():
            raise RuntimeError('Observability runtime is not ready')
        try:
            return await self.runtime.run_normalization_replay(
                raw_table=raw_table,
                batch_limit=batch_limit,
                after_sequence=after_sequence,
                ignore_cursor=ignore_cursor,
                max_batches=max_batches,
                reprocess_reason=reprocess_reason,
            )
        except Exception as error:
            self.status.mark_component_degraded(
                self.status.COMPONENT_NORMALIZER,
                error,
            )
            self.status.mark_degraded(error)
            raise

    async def run_market_derivation_replay(
        self,
        *,
        raw_table: str | None,
        batch_limit: int | None,
        after_sequence: int | None = None,
        ignore_cursor: bool = False,
        max_batches: int | None,
        reprocess_reason: str | None,
    ) -> dict[str, object]:
        if not self.has_started_runtime():
            raise RuntimeError('Observability runtime is not ready')
        try:
            return await self.runtime.run_market_derivation_replay(
                raw_table=raw_table,
                batch_limit=batch_limit,
                after_sequence=after_sequence,
                ignore_cursor=ignore_cursor,
                max_batches=max_batches,
                reprocess_reason=reprocess_reason,
            )
        except Exception as error:
            self.status.mark_component_degraded(
                self.status.COMPONENT_MARKET_DERIVER,
                error,
            )
            self.status.mark_degraded(error)
            raise

    def snapshot(self) -> dict[str, object]:
        snapshot = self.status.snapshot()
        snapshot['starting_in_background'] = self._start_task is not None and not self._start_task.done()
        snapshot['recovery_allowed'] = self.runtime is not None
        return snapshot

    def has_started_runtime(self) -> bool:
        return self.runtime is not None and self.runtime.is_started()

    def _apply_stage_results(self, stage_results: dict[str, dict[str, object]]) -> None:
        component_map = {
            'schema': self.status.COMPONENT_SCHEMA,
            'registry': self.status.COMPONENT_REGISTRY,
            'startup_catch_up': self.status.COMPONENT_STARTUP_CATCH_UP,
            'listener': self.status.COMPONENT_LISTENER,
            'decode_scheduler': self.status.COMPONENT_DECODE_SCHEDULER,
            'normalizer': self.status.COMPONENT_NORMALIZER,
            'market_deriver': self.status.COMPONENT_MARKET_DERIVER,
        }
        for stage_name, component_name in component_map.items():
            result = stage_results.get(stage_name)
            if result is None:
                self.status.mark_component_skipped(component_name, f'{stage_name} was not executed')
                continue
            if result.get('status') == 'degraded':
                self.status.mark_component_degraded(component_name, result.get('error') or f'{stage_name} failed')
                continue
            self.status.mark_component_ready(component_name)
