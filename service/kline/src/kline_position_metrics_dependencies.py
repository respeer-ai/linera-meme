from query.read_models.position_metrics_product_state_query_input_provider import (
    PositionMetricsProductStateQueryInputProvider,
)


class KlinePositionMetricsDependencies:
    def __init__(
        self,
        *,
        positions_repository,
        snapshot_inputs_repository,
        replay_facts_repository,
        pool_history_repository,
        query_input_provider,
        fetcher_override,
    ):
        self._positions_repository = positions_repository
        self._snapshot_inputs_repository = snapshot_inputs_repository
        self._replay_facts_repository = replay_facts_repository
        self._pool_history_repository = pool_history_repository
        self._query_input_provider = query_input_provider
        self._fetcher_override = fetcher_override

    @classmethod
    def resolve(cls, *, runtime, overrides):
        positions_repository_builder = overrides.get('positions_repository_builder')
        positions_repository = (
            positions_repository_builder() if positions_repository_builder is not None else None
        )
        if positions_repository is None:
            positions_repository = runtime.position_metrics_positions_projection_repository()

        snapshot_inputs_repository_builder = overrides.get('snapshot_inputs_repository_builder')
        snapshot_inputs_repository = (
            snapshot_inputs_repository_builder() if snapshot_inputs_repository_builder is not None else None
        )
        if snapshot_inputs_repository is None:
            snapshot_inputs_repository = runtime.position_metrics_snapshot_inputs_projection_repository()

        replay_facts_repository_builder = overrides.get('replay_facts_repository_builder')
        replay_facts_repository = (
            replay_facts_repository_builder() if replay_facts_repository_builder is not None else None
        )
        if replay_facts_repository is None:
            replay_facts_repository = runtime.position_metrics_replay_facts_projection_repository()

        pool_history_repository_builder = overrides.get('pool_history_repository_builder')
        pool_history_repository = (
            pool_history_repository_builder() if pool_history_repository_builder is not None else None
        )
        if pool_history_repository is None:
            pool_history_repository = runtime.settled_pool_history_projection_repository()

        fetcher_override = overrides.get('fetcher_override')
        query_input_provider = None
        if fetcher_override is None:
            query_input_provider = PositionMetricsProductStateQueryInputProvider(
                snapshot_inputs_repository=snapshot_inputs_repository,
                replay_facts_repository=replay_facts_repository,
            )

        return cls(
            positions_repository=positions_repository,
            snapshot_inputs_repository=snapshot_inputs_repository,
            replay_facts_repository=replay_facts_repository,
            pool_history_repository=pool_history_repository,
            query_input_provider=query_input_provider,
            fetcher_override=fetcher_override,
        )

    def positions_repository(self):
        return self._positions_repository

    def snapshot_inputs_repository(self):
        return self._snapshot_inputs_repository

    def replay_facts_repository(self):
        return self._replay_facts_repository

    def pool_history_repository(self):
        return self._pool_history_repository

    def query_input_provider(self):
        return self._query_input_provider

    def fetcher_override(self):
        return self._fetcher_override

    def fetcher(self, *, position_metrics_public_api):
        if self._fetcher_override is not None:
            return self._fetcher_override
        return position_metrics_public_api.build_fetcher(
            query_input_provider=self._query_input_provider,
        )
