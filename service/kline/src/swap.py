import async_request
from environment import running_in_k8s
from request_trace import persist_http_trace


class Account:
    def __init__(self, _dict):
        self.chain_id = _dict['chain_id']
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
            return float(self.amount_1_in) / float(self.amount_0_in) if token_reversed is False else float(self.amount_0_in) / float(self.amount_1_in)
        if self.transaction_type == 'RemoveLiquidity':
            return float(self.amount_1_out) / float(self.amount_0_out) if token_reversed is False else float(self.amount_0_out) / float(self.amount_1_out)

        volume = self.base_volume(token_reversed)
        turnover = self.quote_volume(token_reversed)

        return float(turnover) / float(volume)

    def quote_volume(self, token_reversed: bool):
        if token_reversed is False:
            return self.amount_1_in if self.transaction_type == 'BuyToken0' else self.amount_1_out
        else:
            return self.amount_0_out if self.transaction_type == 'BuyToken0' else self.amount_0_in

    def base_volume(self, token_reversed: bool):
        if token_reversed is False:
            return self.amount_0_out if self.transaction_type == 'BuyToken0' else self.amount_0_in
        else:
            return self.amount_1_in if self.transaction_type == 'BuyToken0' else self.amount_1_out

    def turnover(self, token_reversed: bool):
        return self.quote_volume(token_reversed)

    def volume(self, token_reversed: bool):
        return self.base_volume(token_reversed)

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

    async def swap(self, amount_0: str = None, amount_1: str = None):
        amount_0 = '{:.18f}'.format(amount_0) if amount_0 is not None else None
        amount_1 = '{:.18f}'.format(amount_1) if amount_1 is not None else None

        payload = {
            'query': f'mutation {{\n swap(amount0In: "{amount_0}") \n}}'
        } if amount_0 is not None else {
            'query': f'mutation {{\n swap(amount1In: "{amount_1}") \n}}'
        }
        url = self.wallet_application_url()
        try:
            resp = await async_request.post(url=url, json=payload, timeout=(3, 10))
            payload_json = resp.json() if resp.text else {}
            persist_http_trace(
                getattr(self.wallet, 'db', None),
                source='maker',
                component='swap',
                operation='swap',
                target='wallet_application_mutation',
                request_url=url,
                request_payload=payload,
                response=resp,
                owner=getattr(self.wallet, 'owner', None),
                pool_application=f'{self.pool_application.chain_id}:{self.pool_application.owner}',
                pool_id=self.pool_id,
                details={
                    'token_0': self.token_0,
                    'token_1': self.token_1 if self.token_1 is not None else 'TLINERA',
                    'graphql_errors': payload_json.get('errors') if isinstance(payload_json, dict) else None,
                },
            )
            if 'errors' in payload_json:
                print(f'Failed swap: {resp.text}')
                return False
            return resp.ok is True
        except Exception as e:
            print(f'{url}, {payload} -> ERROR: {e}')
            persist_http_trace(
                getattr(self.wallet, 'db', None),
                source='maker',
                component='swap',
                operation='swap',
                target='wallet_application_mutation',
                request_url=url,
                request_payload=payload,
                error=str(e),
                owner=getattr(self.wallet, 'owner', None),
                pool_application=f'{self.pool_application.chain_id}:{self.pool_application.owner}',
                pool_id=self.pool_id,
                details={
                    'token_0': self.token_0,
                    'token_1': self.token_1 if self.token_1 is not None else 'TLINERA',
                },
            )
            return False


class Swap:
    def __init__(self, host: str, chain_id: str, application_id: str, wallet, db=None):
        self.host = host
        self.base_url = f'http://{host}' + ('/api/swap' if not running_in_k8s() else '')
        self.chain = chain_id
        self.application = application_id
        self.wallet = wallet
        self.db = db if db is not None else getattr(wallet, 'db', None)

    def application_url(self) -> str:
        prefix = '' if running_in_k8s() else '/query'
        return f'{self.base_url}{prefix}/chains/{self.chain}/applications/{self.application}'

    async def get_pools(self) -> list[Pool]:
        payload = {
            'query': 'query {\n pools {\n poolId\n token0\n token1\n poolApplication\n latestTransaction\n token0Price\n token1Price\n reserve0\n reserve1\n }\n}'
        }
        try:
            url = self.application_url()
            resp = await async_request.post(url=url, json=payload, timeout=(3, 10))
            payload_json = resp.json() if resp.text else {}
            persist_http_trace(
                self.db,
                source='kline' if self.wallet is None else 'maker',
                component='swap',
                operation='get_pools',
                target='swap_query',
                request_url=url,
                request_payload=payload,
                response=resp,
                owner=getattr(self.wallet, 'owner', None),
                details={
                    'swap_chain': self.chain,
                    'swap_application': self.application,
                    'graphql_errors': payload_json.get('errors') if isinstance(payload_json, dict) else None,
                },
            )
            if 'errors' in payload_json:
                print(f'Failed swap: {resp.text}')
        except Exception as e:
            url = self.application_url()
            print(f'{url}, {payload} -> ERROR: {e}')
            persist_http_trace(
                self.db,
                source='kline' if self.wallet is None else 'maker',
                component='swap',
                operation='get_pools',
                target='swap_query',
                request_url=url,
                request_payload=payload,
                error=str(e),
                owner=getattr(self.wallet, 'owner', None),
                details={
                    'swap_chain': self.chain,
                    'swap_application': self.application,
                },
            )
            return []
        return [Pool(v, self.wallet) for v in payload_json['data']['pools'] if v['reserve0'] is not None and v['reserve1'] is not None ]

    async def get_pool_transactions(self, pool: Pool, start_id: int = None) -> list[Transaction]:
        payload = {
            'query': f'query {{\n latestTransactions(startId:{start_id}) \n}}'
        } if start_id is not None else {
            'query': 'query {\n latestTransactions \n}'
        }
        prefix = '' if running_in_k8s() else '/query'
        url = f'{self.base_url}{prefix}/chains/{pool.pool_application.chain_id}/applications/{pool.pool_application.short_owner}'
        resp = await async_request.post(url=url, json=payload, timeout=(3, 10))
        payload_json = resp.json() if resp.text else {}
        persist_http_trace(
            self.db,
            source='kline' if self.wallet is None else 'maker',
            component='swap',
            operation='get_pool_transactions',
            target='pool_query',
            request_url=url,
            request_payload=payload,
            response=resp,
            owner=getattr(self.wallet, 'owner', None),
            pool_application=f'{pool.pool_application.chain_id}:{pool.pool_application.owner}',
            pool_id=pool.pool_id,
            details={
                'start_id': start_id,
                'graphql_errors': payload_json.get('errors') if isinstance(payload_json, dict) else None,
            },
        )

        return [Transaction(v) for v in payload_json['data']['latestTransactions']]
