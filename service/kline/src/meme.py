import requests

class Meme:
    def __init__(self, host, wallet):
        self.host = host
        self.wallet = wallet
        self.base_url = f'http://{host}/api/proxy'

    # chain_id: token creator chain id
    # token: token application id
    def balance(self, owner, chain_id, token):
        json = {
            'query': f'query {{\n balanceOf(\n owner: "{owner}") \n}}'
        }

        url = f'{self.base_url}/chains/{chain_id}/applications/{token}'
        resp = requests.post(url=url, json=json)
        if resp.ok is not True:
            print(f'{url}, {json} -> {resp.reason}')
            return None
        return resp.json()['data']['balanceOf']

    # chain_id: wallet chain id
    # token: token application id
    def creator_chain_id(self, chain_id, token):
        json = {
            'query': f'query {{\n creatorChainId \n}}'
        }

        url = f'{self.wallet._wallet_url()}/chains/{chain_id}/applications/{token}'
        resp = requests.post(url=url, json=json)
        if resp.ok is not True:
            print(f'{url}, {json} -> {resp.reason}')
            return None
        return resp.json()['data']['creatorChainId']
