import async_request
from environment import running_in_k8s

class MemeApplication:
    def __init__(self, dict):
        self.chain_id = dict['chainId']
        self.token = dict['token']


class Proxy:
    def __init__(self, host, application_id, wallet):
        self.host = host
        self.base_url = f'http://{host}' + ('/api/proxy' if not running_in_k8s() else '')
        self.application = application_id if len(application_id) > 0 else None
        self.wallet = wallet
        self.chain = None

    def application_url(self) -> str:
        return f'{self.base_url}/chains/{self.chain}/applications/{self.application}'

    async def get_proxy_chain(self):
        json = {
            'query': 'query {\n chains {\n default\n }\n}'
        }
        resp = await async_request.post(url=self.base_url, json=json, timeout=(3, 10))
        self.chain = resp.json()['data']['chains']['default']
        print('---------------------------------------------------------------------------------------------------------')
        print(f'       Proxy chain: {self.chain}')
        print('---------------------------------------------------------------------------------------------------------')

    async def check_proxy_application(self, application_id: str) -> bool:
        json = {
            'query': 'query {\n memeBytecodeId\n}'
        }
        url = f'{self.base_url}/chains/{self.chain}/applications/{application_id}'
        try:
            resp = await async_request.post(url=url, json=json, timeout=(3, 10))
            return 'errors' not in resp.json()
        except Exception as e:
            print(f'{url}, {json} -> ERROR {e}')
            return False

    async def get_proxy_application(self):
        json = {
            'query': f'query {{\n applications(chainId:"{self.chain}") {{\n id\n }}\n}}'
        }
        resp = await async_request.post(url=self.base_url, json=json, timeout=(3, 10))

        application_ids = [v['id'] for v in resp.json()['data']['applications']]
        for application_id in application_ids:
            if self.check_proxy_application(application_id) is True:
                self.application = application_id
                break
        print('---------------------------------------------------------------------------------------------------------')
        print(f'       Proxy application: {self.application}')
        print('---------------------------------------------------------------------------------------------------------')
        if self.application is None:
            raise Exception('Invalid proxy application')

    async def get_memes(self) -> list[MemeApplication]:
        json = {
            'query': 'query {\n memeApplications { chainId token } \n}'
        }
        url = f'{self.base_url}/chains/{self.chain}/applications/{self.application}'
        try:
            resp = await async_request.post(url=url, json=json, timeout=(3, 10))
            if 'errors' in resp.json():
                print(f'Failed proxy: {resp.text}')
        except Exception as e:
            print(f'{url}, {json} -> ERROR {e}')
            return []

        return [MemeApplication(v) for v in resp.json()['data']['memeApplications']]

