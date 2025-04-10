import requests


class Account:
    def __init__(self, _dict):
        self.chain_id = _dict['chainId']
        self.owner = _dict['owner']
        self.short_owner = self.owner[2:]


class Transaction:
    def __init__(self, _dict):
        self.transaction_id = _dict['transactionId']
        self.transaction_type = _dict['transactionType']
        self.from_ = Account(_dict['from'])
        self.amount_0_in = _dict['amount0In']
        self.amount_1_in = _dict['amount1In']
        self.amount_0_out = _dict['amount0Out']
        self.amount_1_out = _dict['amount1Out']
        self.liquidity = _dict['liquidity']
        self.created_at = _dict['createdAt']

    def direction(self, token_reversed: bool):
        if self.transaction_type == 'AddLiquidity':
            return 'Deposit'
        elif self.transaction_type == 'RemoveLiquidity':
            return 'Burn'
        elif self.transaction_type == 'BuyToken0':
            return 'Buy' if token_reversed is False else 'Sell'
        elif self.transaction_type == 'SellToken0':
            return 'Sell' if token_reversed is False else 'Buy'
        else:
            raise Exception('Invalid transaction type')

    def price(self, token_reversed: bool):
        if self.transaction_type == 'AddLiquidity':
            return float(self.amount_0_in) / float(self.amount_1_in) if token_reversed is False else float(self.amount_1_in) / float(self.amount_0_in)
        if self.transaction_type == 'RemoveLiquidity':
            return float(self.amount_0_out) / float(self.amount_1_out) if token_reversed is False else float(self.amount_1_out) / float(self.amount_0_out)

        volume = self.volume(token_reverse)
        turnover = self.turnover(token_reverse)

        return turnover / volume

    def turnover(self, token_reversed: bool):
        if token_reversed is False:
            return self.amount_1_in if self.transaction_type == 'BuyToken0' else self.amount_1_out
        else:
            return self.amount_0_in if self.transaction_type == 'BuyToken0' else self.amount_0_out

    def volume(self, token_reversed: bool):
        if token_reversed is False:
            return self.amount_0_out if self.transaction_type == 'BuyToken0' else self.amount_0_in
        else:
            return self.amount_1_out if self.transaction_type == 'BuyToken0' else self.amount_1_in

    def record_reverse(self):
        return self.transaction_type == 'BuyToken0' or self.transaction_type == 'SellToken0'


class Pool:
    def __init__(self, _dict, wallet):
        self.wallet = wallet

        self.pool_id = _dict['poolId']
        self.token_0 = _dict['token0']
        self.token_1 = _dict['token1']
        self.pool_application = Account(_dict['poolApplication'])
        self.latest_transaction = Transaction(_dict['latestTransaction']) if _dict['latestTransaction'] is not None else None
        self.token_0_price = _dict['token0Price']
        self.token_1_price = _dict['token1Price']
        self.reserve_0 = _dict['reserve0']
        self.reserve_1 = _dict['reserve1']

    def wallet_application_url(self):
        return f'{self.wallet._wallet_url()}/chains/{self.wallet._chain()}/applications/{self.pool_application.short_owner}'

    def swap(self, amount_0: str = None, amount_1: str = None):
        json = {
            'query': f'mutation {{\n swap(amount0In: "{amount_0}") \n}}'
        } if amount_0 is not None else {
            'query': f'mutation {{\n swap(amount1In: "{amount_1}") \n}}'
        }
        requests.post(url=self.wallet_application_url(), json=json)


class Swap:
    def __init__(self, host: str, application_id: str, wallet):
        self.host = host
        self.chain_id = None
        self.application_id = None
        self.base_url = f'http://{host}/api/swap'
        self.chain = None
        self.application = application_id if len(application_id) > 0 else None
        self.wallet = wallet

    def application_url(self) -> str:
        return f'{self.base_url}/chains/{self.chain}/applications/{self.application}'

    def get_pools(self) -> list[Pool]:
        json = {
            'query': 'query {\n pools {\n poolId\n token0\n token1\n poolApplication\n latestTransaction\n token0Price\n token1Price\n reserve0\n reserve1\n }\n}'
        }
        resp = requests.post(url=self.application_url(), json=json)
        return [Pool(v, self.wallet) for v in resp.json()['data']['pools']]

    def get_pool_transactions(self, pool: Pool, start_id: int = None) -> list[Transaction]:
        json = {
            'query': f'query {{\n latestTransactions(startId:{start_id}) \n}}'
        } if start_id is not None else {
            'query': f'query {{\n latestTransactions \n}}'
        }
        url = f'{self.base_url}/chains/{pool.pool_application.chain_id}/applications/{pool.pool_application.short_owner}'
        resp = requests.post(url=url, json=json)
        return [Transaction(v) for v in resp.json()['data']['latestTransactions']]

    def get_swap_chain(self):
        json = {
            'query': 'query {\n chains {\n default\n }\n}'
        }
        resp = requests.post(url=self.base_url, json=json)
        self.chain = resp.json()['data']['chains']['default']
        print('---------------------------------------------------------------------------------------------------------')
        print(f'       Swap chain: {self.chain}')
        print('---------------------------------------------------------------------------------------------------------')

    def check_swap_application(self, application_id: str) -> bool:
        json = {
            'query': 'query {\n poolId\n}'
        }
        url = f'{self.base_url}/chains/{self.chain}/applications/{application_id}'
        try:
            resp = requests.post(url=url, json=json)
            return 'errors' not in resp.json()
        except Exception as e:
            return False

    def get_swap_application(self):
        json = {
            'query': f'query {{\n applications(chainId:"{self.chain}") {{\n id\n }}\n}}'
        }
        resp = requests.post(url=self.base_url, json=json)

        application_ids = [v['id'] for v in resp.json()['data']['applications']]
        for application_id in application_ids:
            if self.check_swap_application(application_id) is True:
                self.application = application_id
                break
        print('---------------------------------------------------------------------------------------------------------')
        print(f'       Swap application: {self.application}')
        print('---------------------------------------------------------------------------------------------------------')
        if self.application is None:
            raise Exception('Invalid swap application')


