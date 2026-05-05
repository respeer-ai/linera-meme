import async_request
from request_trace import persist_http_trace

class Meme:
    def __init__(self, host, wallet, query_base_url: str | None = None):
        self.host = host
        self.wallet = wallet
        self.db = getattr(wallet, 'db', None)
        self.query_base_url = self._resolve_query_base_url(host, query_base_url)

    def _resolve_query_base_url(self, host: str, query_base_url: str | None) -> str:
        if query_base_url is not None:
            return str(query_base_url).rstrip('/')
        return f'http://{host}/api/proxy/query'

    # chain_id: token creator chain id
    # token: token application id
    async def balance(self, owner, chain_id, token):
        payload = {
            'query': f'query {{\n balanceOf(\n owner: {owner}) \n}}'
        }

        url = f'{self.query_base_url}/chains/{chain_id}/applications/{token}'
        resp = await async_request.post(url=url, json=payload, timeout=(3, 10))
        payload_json = resp.json() if resp.text else {}
        persist_http_trace(
            self.db,
            source='maker',
            component='meme',
            operation='balance',
            target='proxy_query',
            request_url=url,
            request_payload=payload,
            response=resp,
            owner=self.wallet.owner,
            details={
                'token': token,
                'token_chain': chain_id,
                'graphql_errors': payload_json.get('errors') if isinstance(payload_json, dict) else None,
            },
        )
        if resp.ok is not True:
            print(f'{url}, {payload} -> {resp.reason}')
            return None
        return payload_json['data']['balanceOf']

    async def mining_started(self, chain_id, token):
        payload = {
            'query': 'query {\n miningInfo { miningStarted } \n}'
        }

        url = f'{self.query_base_url}/chains/{chain_id}/applications/{token}'
        resp = await async_request.post(url=url, json=payload, timeout=(3, 10))
        payload_json = resp.json() if resp.text else {}
        persist_http_trace(
            self.db,
            source='maker',
            component='meme',
            operation='mining_started',
            target='proxy_query',
            request_url=url,
            request_payload=payload,
            response=resp,
            owner=self.wallet.owner,
            details={
                'token': token,
                'token_chain': chain_id,
                'graphql_errors': payload_json.get('errors') if isinstance(payload_json, dict) else None,
            },
        )
        if resp.ok is not True:
            print(f'{url}, {payload} -> {resp.reason}')
            return None
        return payload_json['data']['miningInfo']['miningStarted']

    # chain_id: wallet chain id
    # token: token application id
    async def creator_chain_id(self, chain_id, token):
        payload = {
            'query': 'query {\n creatorChainId \n}'
        }

        url = f'{self.wallet._wallet_url()}/chains/{chain_id}/applications/{token}'
        resp = await async_request.post(url=url, json=payload, timeout=(3, 10))
        payload_json = resp.json() if resp.text else {}
        persist_http_trace(
            self.db,
            source='maker',
            component='meme',
            operation='creator_chain_id',
            target='wallet_application_query',
            request_url=url,
            request_payload=payload,
            response=resp,
            owner=self.wallet.owner,
            details={
                'wallet_chain': chain_id,
                'token': token,
                'graphql_errors': payload_json.get('errors') if isinstance(payload_json, dict) else None,
            },
        )
        if resp.ok is not True:
            print(f'{url}, {payload} -> {resp.reason}')
            return None
        return payload_json['data']['creatorChainId']
