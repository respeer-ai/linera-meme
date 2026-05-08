class ObservabilityFacade:
    def __init__(self, supervisor):
        self.supervisor = supervisor

    async def recover(self) -> dict[str, object]:
        started = await self.supervisor.recover()
        return {
            'recovered': started,
            'status': self.supervisor.snapshot(),
        }

    async def run_catch_up(
        self,
        *,
        chain_id: str | None,
        max_blocks: int | None,
    ) -> dict[str, object]:
        return await self.supervisor.run_catch_up(
            chain_id=chain_id,
            max_blocks=max_blocks,
        )

    async def run_normalization_replay(
        self,
        *,
        raw_table: str | None,
        batch_limit: int | None,
        after_sequence: int | None,
        max_batches: int | None,
        reprocess_reason: str | None,
    ) -> dict[str, object]:
        return await self.supervisor.run_normalization_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            after_sequence=after_sequence,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )

    async def run_market_derivation_replay(
        self,
        *,
        raw_table: str | None,
        batch_limit: int | None,
        after_sequence: int | None,
        max_batches: int | None,
        reprocess_reason: str | None,
    ) -> dict[str, object]:
        return await self.supervisor.run_market_derivation_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            after_sequence=after_sequence,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )

    def get_debug_observability(
        self,
        *,
        chain_ids: tuple[str, ...],
        run_statuses: tuple[str, ...],
        anomaly_statuses: tuple[str, ...],
        limit: int,
    ) -> dict[str, object]:
        payload = {
            'status': self.supervisor.snapshot(),
            'operator_actions': [],
            'chain_ids': list(chain_ids),
            'run_statuses': list(run_statuses),
            'anomaly_statuses': list(anomaly_statuses),
            'cursors': [],
            'processing_cursors': [],
            'recent_runs': [],
            'anomalies': [],
        }
        payload['operator_actions'] = self._build_operator_actions(payload['status'])
        runtime = self.supervisor.runtime
        if runtime is None or not self.supervisor.has_started_runtime():
            return payload
        try:
            exported_payload = runtime.export_debug_observability(
                chain_ids=chain_ids,
                run_statuses=run_statuses,
                anomaly_statuses=anomaly_statuses,
                limit=limit,
            )
            exported_payload.pop('status', None)
            payload.update(exported_payload)
            self.supervisor.status.mark_component_ready(
                self.supervisor.status.COMPONENT_DEBUG_EXPORT
            )
            payload['status'] = self.supervisor.snapshot()
            payload['operator_actions'] = self._build_operator_actions(payload['status'])
        except Exception as error:
            self.supervisor.status.mark_component_degraded(
                self.supervisor.status.COMPONENT_DEBUG_EXPORT,
                error,
            )
            self.supervisor.status.mark_degraded(error)
            payload['status'] = self.supervisor.snapshot()
            payload['operator_actions'] = self._build_operator_actions(payload['status'])
        return payload

    def _build_operator_actions(self, status: dict[str, object]) -> list[dict[str, str]]:
        if not status.get('configured', False):
            return [{
                'action': 'configure_observability',
                'reason': 'observability is disabled because no chain GraphQL config is present',
            }]

        actions = []
        components = status.get('components', {})
        if status.get('state') == 'degraded' and status.get('recovery_allowed'):
            actions.append({
                'action': 'call_debug_observability_recover',
                'reason': 'observability runtime is degraded and supports in-process recovery',
            })
        if self._component_is_degraded(components, 'schema'):
            actions.append({
                'action': 'check_mysql_schema_and_permissions',
                'reason': 'schema stage failed; validate MySQL availability, table capacity, and DDL permissions',
            })
        if self._component_is_degraded(components, 'registry'):
            actions.append({
                'action': 'check_application_registry_seed_inputs',
                'reason': 'registry bootstrap failed; validate configured application ids and registry storage',
            })
        if self._component_is_degraded(components, 'startup_catch_up'):
            actions.append({
                'action': 'run_targeted_catch_up_or_inspect_chain_client',
                'reason': 'startup catch-up failed; inspect chain GraphQL reachability and repair with explicit catch-up',
            })
        if self._component_is_degraded(components, 'listener'):
            actions.append({
                'action': 'check_graphql_ws_connectivity',
                'reason': 'notification listener failed; inspect WebSocket endpoint and reconnect path',
            })
        if self._component_is_degraded(components, 'debug_export'):
            actions.append({
                'action': 'inspect_raw_repo_read_path',
                'reason': 'debug export failed; inspect diagnostics read queries without assuming ingestion is down',
            })
        if self._component_is_degraded(components, 'normalizer'):
            actions.append({
                'action': 'run_normalization_replay_or_inspect_layer2_cursor',
                'reason': 'normalizer path failed; inspect processing cursors and retry Layer 2 replay explicitly',
            })
        if self._component_is_degraded(components, 'market_deriver'):
            actions.append({
                'action': 'run_market_derivation_replay_or_inspect_layer3_cursor',
                'reason': 'market derivation failed; inspect processing cursors and retry Layer 3 replay explicitly',
            })
        if not actions:
            actions.append({
                'action': 'none',
                'reason': 'observability is healthy or no explicit operator action is required',
            })
        return actions

    def _component_is_degraded(self, components: dict[str, object], component_name: str) -> bool:
        component = components.get(component_name)
        if not isinstance(component, dict):
            return False
        return component.get('status') == 'degraded'

    def _component_is_planned(self, components: dict[str, object], component_name: str) -> bool:
        component = components.get(component_name)
        if not isinstance(component, dict):
            return False
        return component.get('status') == 'planned'
