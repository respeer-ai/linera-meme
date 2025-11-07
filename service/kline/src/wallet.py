import async_request
import subprocess
import os
import shutil


class Wallet:
    def __init__(self, wallet_host, owner, chain, faucet):
        self.wallet_host = wallet_host
        self.wallet_url = f'http://{wallet_host}'
        self.owner = owner
        self.chain = chain
        self.faucet = faucet
        self.wallet_path = '/tmp/linera-wallet'
        self.wallet_index = 0

    def account(self):
        return f'{self.chain}:{self.owner}'

    def _chain(self):
        return self.chain

    def _wallet_url(self):
        return self.wallet_url

    async def balance(self):
        chain_owners = f'''[{{
            chainId: "{self.chain}",
            owners: ["{self.owner}"]
        }}]'''
        json = {
            'query': f'query {{\n balances(chainOwners:{chain_owners}) \n}}'
        }
        try:
            resp = await async_request.post(self.wallet_url, json=json, timeout=(3, 10))
        except Exception as e:
            print(f'{self.wallet_url}, {json} -> ERROR: {e}')
            return 0

        if resp.ok is not True:
            print(f'{self.wallet_url}, {json} -> {resp.reason}')
            return 0

        if 'data' not in resp.json():
            return 0

        balances = resp.json()['data']['balances']
        if self.chain not in balances:
            print(f'{self.chain} not in wallet {self.wallet_url}: {resp.text}')
            return 0

        balances = balances[self.chain]
        chain_balance = float(balances['chainBalance']) if 'chainBalance' in balances else 0

        balances = balances['ownerBalances']
        owner_balance = float(balances[self.owner]) if self.owner in balances else 0

        return chain_balance + owner_balance

    async def open_chain(self):
        payload = {
            'query': f'''mutation {{ claim(owner: "{self.owner}") {{
                chainId
            }} }}'''
        }

        resp = await async_request.post(url=self.faucet, json=payload, timeout=(3, 10))
        if 'data' not in resp.json():
            raise Exception('Failed open chain')

        return resp.json()['data']['claim']['chainId']

    def open_chain_with_cli(self):
        self.wallet_index += 1

        wallet_path = f'{self.wallet_path}/{self.wallet_index}'
        shutil.rmtree(wallet_path, ignore_errors=True)

        os.environ['LINERA_WALLET'] = f'{wallet_path}/wallet.json'
        os.environ['LINERA_KEYSTORE'] = f'{wallet_path}/keystore.json'
        os.environ['LINERA_STORAGE'] = f'rocksdb://{wallet_path}/client.db'

        os.makedirs(wallet_path)

        # Remove exists wallet
        command = ['linera', 'wallet', 'init', '--faucet', self.faucet]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, errors = proc.communicate()
        if proc.returncode != 0 and errors != '':
            raise Exception(errors)

        command = ['linera', 'wallet', 'request-chain', '--faucet', self.faucet]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        output, errors = proc.communicate()
        if proc.returncode != 0 and errors != '':
            raise Exception(errors)

        return(output.splitlines()[0])


    def transfer_with_cli(self, from_chain_id, to_chain_id, amount):
        os.environ['LINERA_WALLET'] = f'{self.wallet_path}/{self.wallet_index}/wallet.json'
        os.environ['LINERA_KEYSTORE'] = f'{self.wallet_path}/{self.wallet_index}/keystore.json'
        os.environ['LINERA_STORAGE'] = f'rocksdb://{self.wallet_path}/{self.wallet_index}/client.db'

        command = ['linera', 'transfer', '--from', from_chain_id, '--to', to_chain_id, amount]
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        output, errors = proc.communicate()
        if proc.returncode != 0 and errors != '':
            raise Exception(errors)
