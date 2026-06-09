class PositionMetricsPublicApi:
    def __init__(
        self,
        *,
        replay_entrypoint,
        fetcher_factory,
        default_swap_out_tolerance_attos,
    ):
        self.replay_entrypoint = replay_entrypoint
        self.fetcher_factory = fetcher_factory
        self.default_swap_out_tolerance_attos = default_swap_out_tolerance_attos

    def build_fetcher(
        self,
        *,
        query_input_provider,
    ):
        return self.fetcher_factory.build(
            query_input_provider=query_input_provider,
        )

    def inspect_pool_history_replay(
        self,
        pool_transaction_history: list[dict],
        *,
        virtual_initial_liquidity: bool,
        swap_out_tolerance_attos: int | None = None,
    ) -> dict:
        return self.replay_entrypoint.inspect_pool_history_replay(
            pool_transaction_history,
            virtual_initial_liquidity=virtual_initial_liquidity,
            swap_out_tolerance_attos=(
                self.default_swap_out_tolerance_attos
                if swap_out_tolerance_attos is None
                else swap_out_tolerance_attos
            ),
        )
