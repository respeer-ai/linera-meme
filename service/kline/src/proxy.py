import async_request
from environment import running_in_k8s
from request_trace import persist_http_trace

class MemeApplication:
    def __init__(self, dict):
        self.chain_id = dict['chainId']
        self.token = dict['token']


class Proxy:
    def __init__(self, host, chain_id, application_id, db=None):
        self.host = host
        self.base_url = f'http://{host}' + ('/api/proxy' if not running_in_k8s() else '')
        self.application = application_id
        self.chain = chain_id
        self.db = db

    def application_url(self) -> str:
        prefix = '' if running_in_k8s() else '/query'
        return f'{self.base_url}{prefix}/chains/{self.chain}/applications/{self.application}'

    def mutation_application_url(self) -> str:
        prefix = '' if running_in_k8s() else '/mutation'
        return f'{self.base_url}{prefix}/chains/{self.chain}/applications/{self.application}'


    async def get_memes(self) -> list[MemeApplication]:
        payload = {
            'query': 'query {\n memeApplications { chainId token } \n}'
        }
        prefix = '' if running_in_k8s() else '/query'
        url = f'{self.base_url}{prefix}/chains/{self.chain}/applications/{self.application}'
        try:
            resp = await async_request.post(url=url, json=payload, timeout=(3, 10))
            payload_json = resp.json() if resp.text else {}
            persist_http_trace(
                self.db,
                source='maker',
                component='proxy',
                operation='get_memes',
                target='proxy_query',
                request_url=url,
                request_payload=payload,
                response=resp,
                details={
                    'proxy_chain': self.chain,
                    'graphql_errors': payload_json.get('errors') if isinstance(payload_json, dict) else None,
                },
            )
            if 'errors' in payload_json:
                print(f'Failed proxy: {resp.text}')
        except Exception as e:
            print(f'{url}, {payload} -> ERROR {e}')
            persist_http_trace(
                self.db,
                source='maker',
                component='proxy',
                operation='get_memes',
                target='proxy_query',
                request_url=url,
                request_payload=payload,
                error=str(e),
                details={'proxy_chain': self.chain},
            )
            return []

        return [MemeApplication(v) for v in payload_json['data']['memeApplications']]

    async def forget_chain(self, chain_id):
        payload = {
            'query': f'mutation {{\n forgetChain(chainId: "{chain_id}") \n}}'
        }
        url = self.mutation_application_url()
        try:
            resp = await async_request.post(url=url, json=payload, timeout=(3, 10))
            payload_json = resp.json() if resp.text else {}
            persist_http_trace(
                self.db,
                source='maker',
                component='proxy',
                operation='forget_chain',
                target='proxy_mutation',
                request_url=url,
                request_payload=payload,
                response=resp,
                details={
                    'forget_chain_id': chain_id,
                    'graphql_errors': payload_json.get('errors') if isinstance(payload_json, dict) else None,
                },
            )
            if 'errors' in payload_json:
                print(f'Failed proxy: {resp.text}')
                return chain_id
            return payload_json['data']['forgetChain']
        except Exception as e:
            print(f'{url}, {payload} -> ERROR {e}')
            persist_http_trace(
                self.db,
                source='maker',
                component='proxy',
                operation='forget_chain',
                target='proxy_mutation',
                request_url=url,
                request_payload=payload,
                error=str(e),
                details={'forget_chain_id': chain_id},
            )
            return chain_id
