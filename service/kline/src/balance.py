import json
import requests

class Balance:
    def __init__(self, rpc_endpoint):
        self.rpc_endpoint = rpc_endpoint

    def chain_balances(self, chain_ids):
        chain_owners = '['
        for i, chain_id in enumerate(chain_ids):
            chain_owners += f'{"," if i > 0 else ""}{{ chainId: "{chain_id}", owners: [] }}'
        chain_owners += ']'

        payload = {
            'query': f'query {{\n balances(chainOwners:{chain_owners}) \n}}'
        }
        try:
            resp = requests.post(self.rpc_endpoint, json=payload)
        except Exception as e:
            return {}

        if 'data' not in resp.json():
            return {}

        balances = resp.json()['data']['balances']
        _balances = {}

        for chain_id in chain_ids:
            _balances[chain_id] = float(balances[chain_id]['chainBalance']) if chain_id in balances and 'chainBalance' in balances[chain_id] else 0

        return _balances

