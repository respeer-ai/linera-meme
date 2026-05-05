class PositionMetricsPublicApi:
    def __init__(
        self,
        *,
        live_payload_api,
        entrypoint,
        replay_entrypoint,
        fetcher_factory,
        default_post,
        default_swap_out_tolerance_attos,
    ):
        self.live_payload_api = live_payload_api
        self.entrypoint = entrypoint
        self.replay_entrypoint = replay_entrypoint
        self.fetcher_factory = fetcher_factory
        self.default_post = default_post
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

    async def fetch_live_position_metrics(
        self,
        position: dict,
        swap_base_url: str,
        *,
        replay_bundle=None,
        liquidity_history: list[dict] | None = None,
        pool_transaction_history: list[dict] | None = None,
        pool_swap_count_since_open: int | None = None,
        pool_history_gap_summary: dict | None = None,
        post=None,
    ):
        payload = await self.live_payload_api.fetch_payload(
            position,
            swap_base_url,
            post=self.default_post if post is None else post,
        )
        return self.entrypoint.enrich_position_metrics_from_payload(
            position,
            payload,
            replay_bundle=replay_bundle,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=pool_swap_count_since_open,
            pool_history_gap_summary=pool_history_gap_summary,
        )

    def enrich_position_metrics_from_payload(
        self,
        position: dict,
        payload: dict,
        *,
        replay_bundle=None,
        liquidity_history: list[dict] | None = None,
        pool_transaction_history: list[dict] | None = None,
        pool_swap_count_since_open: int | None = None,
        pool_history_gap_summary: dict | None = None,
        position_basis_snapshot: dict | None = None,
        pool_state_snapshot: dict | None = None,
    ):
        return self.entrypoint.enrich_position_metrics_from_payload(
            position,
            payload,
            replay_bundle=replay_bundle,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=pool_swap_count_since_open,
            pool_history_gap_summary=pool_history_gap_summary,
            position_basis_snapshot=position_basis_snapshot,
            pool_state_snapshot=pool_state_snapshot,
        )

    def plan_position_metrics_from_payload(
        self,
        position: dict,
        payload: dict,
    ):
        return self.entrypoint.plan_position_metrics_from_payload(
            position,
            payload,
        )
