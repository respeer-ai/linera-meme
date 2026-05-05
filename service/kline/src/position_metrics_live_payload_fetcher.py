class PositionMetricsLivePayloadFetcher:
    def __init__(
        self,
        *,
        parse_account,
    ):
        self.parse_account = parse_account

    async def fetch(
        self,
        *,
        client,
        owner_account: str,
    ) -> dict:
        return await client.get_position_metrics_payload(
            owner=self.parse_account(owner_account),
        )
