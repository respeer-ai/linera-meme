import async_request

from environment import running_in_k8s


class SwapCatalogClient:
    def __init__(self, *, host: str, chain_id: str, application_id: str):
        self.host = host
        self.chain_id = chain_id
        self.application_id = application_id
        self.base_url = f'http://{host}' + ('/api/swap' if not running_in_k8s() else '')

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
        prefix = '' if running_in_k8s() else '/query'
        return f'{self.base_url}{prefix}/chains/{self.chain_id}/applications/{self.application_id}'
