import async_request


class SwapCatalogClient:
    def __init__(self, *, host: str, chain_id: str, application_id: str, query_base_url: str | None = None):
        self.host = host
        self.chain_id = chain_id
        self.application_id = application_id
        self.query_base_url = self._resolve_query_base_url(host, query_base_url)

    async def list_pools(self) -> list[dict]:
        response = await async_request.post(
            url=self._application_url(),
            json={
                'query': 'query {\n pools {\n poolId\n token0\n token1\n poolApplication\n }\n}',
            },
            timeout=(3, 10),
        )
        response.raise_for_status()
        payload = response.json()
        if 'errors' in payload:
            raise RuntimeError(str(payload['errors']))
        return payload['data']['pools'] or []

    def _application_url(self) -> str:
        return f'{self.query_base_url}/chains/{self.chain_id}/applications/{self.application_id}'

    def _resolve_query_base_url(self, host: str, query_base_url: str | None) -> str:
        if query_base_url is not None:
            return str(query_base_url).rstrip('/')
        return f'http://{host}/api/swap/query'
