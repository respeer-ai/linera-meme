import requests

class MemeApplication:
    def __init__(self, dict):
        self.chain_id = dict['chainId']
        self.token = dict['token']


class Proxy:
    def __init__(self, host, application_id, wallet):
        self.host = host
        self.base_url = f'http://{host}/api/proxy'
        self.application = application_id if len(application_id) > 0 else None
        self.wallet = wallet
        self.chain = None

    def application_url(self) -> str:
        return f'{self.base_url}/chains/{self.chain}/applications/{self.application}'

    def get_proxy_chain(self):
        json = {
            'query': 'query {\n chains {\n default\n }\n}'
        }
        resp = requests.post(url=self.base_url, json=json)
        self.chain = resp.json()['data']['chains']['default']
        print('---------------------------------------------------------------------------------------------------------')
        print(f'       Proxy chain: {self.chain}')
        print('---------------------------------------------------------------------------------------------------------')

    def check_proxy_application(self, application_id: str) -> bool:
        json = {
            'query': 'query {\n memeBytecodeId\n}'
        }
        url = f'{self.base_url}/chains/{self.chain}/applications/{application_id}'
        try:
            resp = requests.post(url=url, json=json)
            return 'errors' not in resp.json()
        except Exception as e:
            return False

    def get_proxy_application(self):
        json = {
            'query': f'query {{\n applications(chainId:"{self.chain}") {{\n id\n }}\n}}'
        }
        resp = requests.post(url=self.base_url, json=json)

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

    def get_memes(self) -> list[MemeApplication]:
        json = {
            'query': f'query {{\n memeApplications {{ chainId token }} \n}}'
        }
        try:
            resp = requests.post(url=url, json=json)
            if 'errors' in resp.json():
                print(f'Failed proxy: {resp.text}')
        except Exception as e:
            return []

        return [MemeApplication(v) for v in resp.json()['data']['memeApplications']]

