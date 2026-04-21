import async_request
from environment import running_in_k8s
from request_trace import persist_http_trace

class Meme:
    def __init__(self, host, wallet):
        self.host = host
        self.wallet = wallet
        self.db = getattr(wallet, 'db', None)
        self.base_url = f'http://{host}' + ('/api/proxy' if not running_in_k8s() else '')

    # chain_id: token creator chain id
    # token: token application id
    async def balance(self, owner, chain_id, token):
        payload = {
            'query': f'query {{\n balanceOf(\n owner: {owner}) \n}}'
        }

        prefix = '' if running_in_k8s() else '/query'
        url = f'{self.base_url}{prefix}/chains/{chain_id}/applications/{token}'
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

        prefix = '' if running_in_k8s() else '/query'
        url = f'{self.base_url}{prefix}/chains/{chain_id}/applications/{token}'
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
