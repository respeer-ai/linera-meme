class PositionMetricsFacadeSupport:
    def __init__(
        self,
        *,
        parse_account,
        running_in_k8s,
        pool_application_client_factory,
        payload_enricher_factory,
    ):
        self.parse_account = parse_account
        self.running_in_k8s = running_in_k8s
        self.pool_application_client_factory = pool_application_client_factory
        self.payload_enricher_factory = payload_enricher_factory

    async def fetch_live_position_metrics(
        self,
        position: dict,
        swap_base_url: str,
        *,
        liquidity_history: list[dict] | None = None,
        pool_transaction_history: list[dict] | None = None,
        pool_swap_count_since_open: int | None = None,
        pool_history_gap_summary: dict | None = None,
        post,
        in_k8s: bool | None = None,
    ):
        owner = self.parse_account(position['owner'])
        payload = await self.pool_application_client_factory(
            base_url=swap_base_url,
            post=post,
            in_k8s=self.running_in_k8s() if in_k8s is None else in_k8s,
        ).get_position_metrics_payload(
            pool_application=position['pool_application'],
            owner=owner,
        )
        return self.enrich_position_metrics_from_payload(
            position,
            payload,
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
        liquidity_history: list[dict] | None = None,
        pool_transaction_history: list[dict] | None = None,
        pool_swap_count_since_open: int | None = None,
        pool_history_gap_summary: dict | None = None,
        position_basis_snapshot: dict | None = None,
        pool_state_snapshot: dict | None = None,
    ):
        return self.payload_enricher_factory().enrich(
            position,
            payload,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=pool_swap_count_since_open,
            pool_history_gap_summary=pool_history_gap_summary,
            position_basis_snapshot=position_basis_snapshot,
            pool_state_snapshot=pool_state_snapshot,
        )
