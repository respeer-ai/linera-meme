class PoolApplicationClient:
    POSITION_METRICS_QUERY = '''
                query PositionMetrics($owner: Account!) {
                  pool
                  totalSupply
                  virtualInitialLiquidity
                  liquidity(owner: $owner) {
                    liquidity
                    amount0
                    amount1
                  }
                }
            '''

    def __init__(
        self,
        *,
        application_url: str,
        post,
    ):
        self.application_url = application_url
        self.post = post

    async def get_position_metrics_payload(
        self,
        *,
        owner: dict,
    ) -> dict:
        payload = await self._post_position_metrics_query(
            url=self.application_url,
            query=self.build_position_metrics_query(owner),
        )
        if 'errors' in payload:
            raise RuntimeError(str(payload['errors']))
        return payload

    @classmethod
    def build_application_url(
        cls,
        *,
        swap_base_url: str,
        pool_application: str,
    ) -> str:
        chain_id, application_id = pool_application.split(':', 1)
        short_application_id = application_id[2:] if application_id.startswith('0x') else application_id
        return f'{swap_base_url}/chains/{chain_id}/applications/{short_application_id}'

    @classmethod
    def build_position_metrics_query(cls, owner: dict) -> dict:
        return {
            'query': cls.POSITION_METRICS_QUERY,
            'variables': {
                'owner': owner,
            },
        }

    async def _post_position_metrics_query(
        self,
        *,
        url: str,
        query: dict,
    ) -> dict:
        response = await self.post(
            url=url,
            json=query,
            timeout=(3, 10),
        )
        response.raise_for_status()
        return response.json()
