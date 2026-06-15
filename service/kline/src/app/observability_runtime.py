from app.bootstrap import AppBootstrap
from app.lifecycle import AppLifecycle


class ObservabilityRuntime:
    def __init__(
        self,
        config,
        *,
        bootstrap: AppBootstrap | None = None,
        lifecycle: AppLifecycle | None = None,
        market_data_event_sink=None,
    ):
        self.config = config
        self.bootstrap = bootstrap or AppBootstrap(market_data_event_sink=market_data_event_sink)
        self.lifecycle = lifecycle or AppLifecycle()
        self.container = None

    async def start(self) -> dict[str, dict[str, object]]:
        if self.container is not None:
            return {}
        container = self.bootstrap.build_container(self.config)
        self.container = container
        try:
            return await self._run_startup_stages(container)
        except Exception:
            try:
                await self.lifecycle.shutdown(container)
            finally:
                self.container = None
            raise

    async def shutdown(self) -> None:
        if self.container is None:
            return
        await self.lifecycle.shutdown(self.container)
        self.container = None

    async def refresh(self) -> dict[str, dict[str, object]]:
        if self.container is None:
            return await self.start()
        return await self._run_refresh_stages(self.container)

    def is_started(self) -> bool:
        return self.container is not None

    def default_max_blocks(self) -> int:
        return self.config.catch_up_max_blocks_per_chain

    def export_debug_observability(
        self,
        *,
        chain_ids: tuple[str, ...],
        run_statuses: tuple[str, ...],
        anomaly_statuses: tuple[str, ...],
        limit: int,
    ) -> dict[str, object]:
        raw_repository = self._require_container_value('raw_repository', 'Raw repository is not initialized')
        return {
            'cursors': raw_repository.list_chain_cursors(
                chain_ids=chain_ids,
                limit=limit,
            ),
            'processing_cursors': self._list_processing_cursors(limit=limit),
            'recent_runs': raw_repository.list_recent_ingest_runs(
                chain_ids=chain_ids,
                statuses=run_statuses,
                limit=limit,
            ),
            'anomalies': raw_repository.list_ingestion_anomalies(
                chain_ids=chain_ids,
                statuses=anomaly_statuses,
                limit=limit,
            ),
        }

    async def run_catch_up(
        self,
        *,
        chain_id: str | None,
        max_blocks: int | None,
    ) -> dict[str, object]:
        if chain_id is not None:
            catch_up_runner = self._require_container_value('catch_up_runner', 'Catch-up runner is not initialized')
            effective_max_blocks = max_blocks or self.default_max_blocks()
            return {
                'trigger': 'admin_repair',
                'scope': 'single_chain',
                'result': await catch_up_runner.ingest_until_caught_up(
                    chain_id,
                    max_blocks=effective_max_blocks,
                    mode='catch_up',
                ),
            }

        catch_up_driver = self._require_container_value('catch_up_driver', 'Catch-up driver is not initialized')
        return {
            'trigger': 'admin_repair',
            'scope': 'configured_chains',
            'result': await catch_up_driver.run_once(max_blocks_per_chain=max_blocks),
        }

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
        replay_driver = self._require_container_value(
            'normalization_replay_driver',
            'Normalization replay driver is not initialized',
        )
        effective_batch_limit = batch_limit or self.config.normalization_replay_batch_limit
        if raw_table is not None:
            return {
                'trigger': 'admin_repair',
                'scope': 'single_raw_table',
                'result': replay_driver.run_until_caught_up(
                    raw_table=raw_table,
                    batch_limit=effective_batch_limit,
                    after_sequence=after_sequence,
                    ignore_cursor=ignore_cursor,
                    max_batches=max_batches,
                    reprocess_reason=reprocess_reason,
                ),
            }
        return {
            'trigger': 'admin_repair',
            'scope': 'configured_raw_tables',
            'result': replay_driver.run_all(
                batch_limit=effective_batch_limit,
                max_batches_per_table=max_batches,
                reprocess_reason=reprocess_reason,
            ),
        }

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
        replay_driver = self._require_container_value(
            'market_derivation_replay_driver',
            'Market derivation replay driver is not initialized',
        )
        effective_batch_limit = batch_limit or self.config.market_derivation_replay_batch_limit
        if raw_table is not None:
            return {
                'trigger': 'admin_repair',
                'scope': 'single_raw_table',
                'result': replay_driver.run_until_caught_up(
                    raw_table=raw_table,
                    batch_limit=effective_batch_limit,
                    after_sequence=after_sequence,
                    ignore_cursor=ignore_cursor,
                    max_batches=max_batches,
                    reprocess_reason=reprocess_reason,
                ),
            }
        return {
            'trigger': 'admin_repair',
            'scope': 'configured_raw_tables',
            'result': replay_driver.run_all(
                batch_limit=effective_batch_limit,
                max_batches_per_table=max_batches,
                reprocess_reason=reprocess_reason,
            ),
        }

    def _require_container_value(self, key: str, error_message: str):
        if self.container is None:
            raise RuntimeError('Observability runtime is not started')
        value = self.container.get(key)
        if value is None:
            raise RuntimeError(error_message)
        return value

    async def _run_startup_stages(self, container: dict[str, object]) -> dict[str, dict[str, object]]:
        results = {}
        results['schema'] = self._run_sync_stage(self.lifecycle.ensure_schema, container)
        results['position_metrics_snapshot_repair'] = self._run_sync_stage(
            self.lifecycle.repair_position_metrics_snapshots,
            container,
        )
        results['registry'] = await self._run_registry_stage(container)
        results['startup_catch_up'] = await self._run_async_stage(self.lifecycle.run_startup_catch_up, container)
        results['listener'] = await self._run_async_stage(self.lifecycle.start_listener, container)
        results['decode_scheduler'] = self._worker_stage_result(
            container,
            required_keys=('decode_scheduler',),
            error_message='decode scheduler is not initialized',
        )
        results['normalizer'] = self._worker_stage_result(
            container,
            required_keys=('normalized_event_materializer', 'normalization_worker', 'processing_cursor_repository'),
            error_message='normalizer worker boundary is not initialized',
        )
        results['market_deriver'] = self._worker_stage_result(
            container,
            required_keys=(
                'settled_trade_repository',
                'settled_liquidity_change_repository',
                'settled_market_materializer',
                'market_derivation_worker',
                'market_derivation_replay_driver',
            ),
            error_message='market derivation worker boundary is not initialized',
        )
        return results

    async def _run_refresh_stages(self, container: dict[str, object]) -> dict[str, dict[str, object]]:
        results = {}
        results['registry'] = await self._run_registry_stage(container)
        return results

    async def _run_registry_stage(self, container: dict[str, object]) -> dict[str, object]:
        seed_result = self._run_sync_stage(self.lifecycle.seed_registry, container)
        if seed_result['status'] == 'degraded':
            return seed_result
        discovery_result = await self._run_async_stage(self.lifecycle.discover_registry, container)
        if discovery_result['status'] == 'degraded':
            return discovery_result
        sync_result = await self._run_sync_or_async_stage(self.lifecycle.sync_discovered_chain_ids, container)
        if sync_result['status'] == 'degraded':
            return sync_result
        return {'status': 'ready', 'error': None}

    def _run_sync_stage(self, operation, container: dict[str, object]) -> dict[str, object]:
        try:
            operation(container)
        except Exception as error:
            return {'status': 'degraded', 'error': str(error)}
        return {'status': 'ready', 'error': None}

    async def _run_async_stage(self, operation, container: dict[str, object]) -> dict[str, object]:
        try:
            await operation(container)
        except Exception as error:
            return {'status': 'degraded', 'error': str(error)}
        return {'status': 'ready', 'error': None}

    async def _run_sync_or_async_stage(self, operation, container: dict[str, object]) -> dict[str, object]:
        try:
            result = operation(container)
            if hasattr(result, '__await__'):
                await result
        except Exception as error:
            return {'status': 'degraded', 'error': str(error)}
        return {'status': 'ready', 'error': None}

    def _worker_stage_result(
        self,
        container: dict[str, object],
        *,
        required_keys: tuple[str, ...],
        error_message: str,
    ) -> dict[str, object]:
        for key in required_keys:
            if container.get(key) is None:
                return {'status': 'degraded', 'error': error_message}
        return {'status': 'ready', 'error': None}

    def _list_processing_cursors(self, *, limit: int) -> list[dict]:
        if self.container is None:
            return []
        repository = self.container.get('processing_cursor_repository')
        if repository is None or not hasattr(repository, 'list_cursors'):
            return []
        return repository.list_cursors(limit=limit)
