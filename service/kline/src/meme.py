import async_request
from environment import running_in_k8s

class Meme:
    def __init__(self, host, wallet):
        self.host = host
        self.wallet = wallet
        self.base_url = f'http://{host}' + ('/api/proxy' if not running_in_k8s() else '')

    # chain_id: token creator chain id
    # token: token application id
    async def balance(self, owner, chain_id, token):
        json = {
            'query': f'query {{\n balanceOf(\n owner: "{owner}") \n}}'
        }

        url = f'{self.base_url}/chains/{chain_id}/applications/{token}'
        resp = await async_request.post(url=url, json=json, timeout=(3, 10))
        if resp.ok is not True:
            print(f'{url}, {json} -> {resp.reason}')
            return None
        return resp.json()['data']['balanceOf']

    async def mining_started(self, chain_id, token):
        json = {
            'query': 'query {\n miningInfo { miningStarted } \n}'
        }

        url = f'{self.base_url}/chains/{chain_id}/applications/{token}'
        resp = await async_request.post(url=url, json=json, timeout=(3, 10))
        if resp.ok is not True:
            print(f'{url}, {json} -> {resp.reason}')
            return None
        return resp.json()['data']['miningInfo']['miningStarted']

    # chain_id: wallet chain id
    # token: token application id
    async def creator_chain_id(self, chain_id, token):
        json = {
            'query': 'query {\n creatorChainId \n}'
        }

        url = f'{self.wallet._wallet_url()}/chains/{chain_id}/applications/{token}'
        resp = await async_request.post(url=url, json=json, timeout=(3, 10))
        if resp.ok is not True:
            print(f'{url}, {json} -> {resp.reason}')
            return None
        return resp.json()['data']['creatorChainId']
