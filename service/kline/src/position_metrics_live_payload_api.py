class PositionMetricsLivePayloadApi:
    def __init__(
        self,
        *,
        account_codec,
        pool_application_client_type,
        payload_fetcher,
    ):
        self.account_codec = account_codec
        self.pool_application_client_type = pool_application_client_type
        self.payload_fetcher = payload_fetcher

    def parse_account(self, account: str):
        return self.account_codec.payload_account_from_public_account(account)

    def build_position_metrics_query(self, owner: dict):
        return self.pool_application_client_type.build_position_metrics_query(owner)

    async def fetch_payload(
        self,
        position: dict,
        swap_base_url: str,
        *,
        post,
    ) -> dict:
        client = self.pool_application_client_type(
            application_url=self.pool_application_client_type.build_application_url(
                swap_base_url=swap_base_url,
                pool_application=position['pool_application'],
            ),
            post=post,
        )
        return await self.payload_fetcher.fetch(
            client=client,
            owner_account=position['owner'],
        )
