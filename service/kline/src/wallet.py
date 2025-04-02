import requests


class Wallet:
    def __init__(self, wallet_host, owner, chain):
        self.wallet_host = wallet_host
        self.wallet_url = f'http://{wallet_host}'
        self.owner = owner
        self.chain = chain

    def account(self):
        return f'{self.chain}:User:{self.owner}'

    def balance(self):
        chain_owners = {
            self.chain: [f'User:{self.owner}']
        }
        chain_owners_str = '{'
        i = 0
        j = 0
        for chain, owners in chain_owners.items():
            chain_owners_str += ('' if i == 0 else ',') + chain + ':['
            for owner in owners:
                chain_owners_str += ('' if i == 0 else ',') + f'"{owner}"'
            chain_owners_str += ']'
        chain_owners_str += '}'

        json = {
            'query': f'query {{\n balances(chainOwners:{chain_owners_str}) \n}}'
        }
        resp = requests.post(self.wallet_url, json=json)
        balances = resp.json()['data']['balances']
        return float(balances[self.chain]['chainBalance']) + float(balances[self.chain]['ownerBalances'][f'User:{self.owner}'])
