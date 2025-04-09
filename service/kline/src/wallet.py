import requests


class Wallet:
    def __init__(self, wallet_host, owner, chain):
        self.wallet_host = wallet_host
        self.wallet_url = f'http://{wallet_host}'
        self.owner = owner
        self.chain = chain

    def account(self):
        return f'{self.chain}:{self.owner}'

    def _chain(self):
        return self.chain

    def _wallet_url(self):
        return self.wallet_url

    def balance(self):
        chain_owners = f'''[{{
            chainId: "{self.chain}",
            owners: ["{self.owner}"]
        }}]'''
        json = {
            'query': f'query {{\n balances(chainOwners:{chain_owners}) \n}}'
        }
        resp = requests.post(self.wallet_url, json=json)
        balances = resp.json()['data']['balances']
        return float(balances[self.chain]['chainBalance']) + float(balances[self.chain]['ownerBalances'][f'{self.owner}'])
