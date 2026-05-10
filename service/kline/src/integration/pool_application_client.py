from account_codec import AccountCodec


class PoolApplicationClient:
    POSITION_METRICS_QUERY = '''
                query PositionMetrics($owner: Account!) {
                  pool {
                    fee_to {
                      chain_id
                      owner
                    }
                  }
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
        account_codec = AccountCodec()
        chain_id = account_codec.chain_id_from_account(pool_application)
        short_application_id = account_codec.application_id_from_account(pool_application)
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
