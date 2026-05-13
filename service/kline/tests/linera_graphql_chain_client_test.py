import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


async_request_stub = types.ModuleType('async_request')


class FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')


async def dummy_post(**_kwargs):
    raise AssertionError('async_request.post should be stubbed by the test')


async_request_stub.post = dummy_post
sys.modules['async_request'] = async_request_stub


import integration.linera_graphql_chain_client as linera_graphql_chain_client_module  # noqa: E402
from integration.block_not_available_error import BlockNotAvailableError  # noqa: E402
from integration.linera_graphql_chain_client import LineraGraphqlChainClient  # noqa: E402


class LineraGraphqlChainClientTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        linera_graphql_chain_client_module.async_request = async_request_stub

    async def test_fetch_block_walks_back_from_tip_and_returns_confirmed_block(self):
        recorded_calls = []

        async def fake_post(**kwargs):
            recorded_calls.append(kwargs)
            query = kwargs['json']['query']
            variables = kwargs['json']['variables']
            if 'query TipHeader' in query:
                return FakeResponse({
                    'data': {
                        'block': {
                            'hash': 'hash-9',
                            'block': {
                                'header': {
                                    'height': 9,
                                },
                            },
                        },
                    },
                })
            if 'query BlockHeaders' in query:
                self.assertEqual(variables['from'], 'hash-9')
                return FakeResponse({
                    'data': {
                        'blocks': [
                            {
                                'hash': 'hash-9',
                                'block': {
                                    'header': {
                                        'height': 9,
                                        'previousBlockHash': 'hash-8',
                                    },
                                },
                            },
                            {
                                'hash': 'hash-8',
                                'block': {
                                    'header': {
                                        'height': 8,
                                        'previousBlockHash': 'hash-7',
                                    },
                                },
                            },
                            {
                                'hash': 'hash-7',
                                'block': {
                                    'header': {
                                        'height': 7,
                                        'previousBlockHash': 'hash-6',
                                    },
                                },
                            },
                        ],
                    },
                })
            if 'query BlockByHash' in query:
                self.assertEqual(variables['hash'], 'hash-7')
                return FakeResponse({
                    'data': {
                        'block': {
                            'hash': 'hash-7',
                            'block': {
                                'header': {
                                    'height': 7,
                                    'timestamp': 1234567890,
                                },
                                'body': {
                                    'messages': [],
                                    'previousMessageBlocks': {},
                                    'previousEventBlocks': {},
                                    'oracleResponses': [],
                                    'events': [],
                                    'blobs': [],
                                    'operationResults': [],
                                    'transactionMetadata': [],
                                },
                            },
                        },
                    },
                })
            raise AssertionError(f'Unexpected query: {query}')

        async_request_stub.post = fake_post
        client = LineraGraphqlChainClient('https://example.com/graphql')

        payload = await client.fetch_block('chain-a', 7)

        self.assertEqual(payload['hash'], 'hash-7')
        self.assertEqual(recorded_calls[0]['url'], 'https://example.com/graphql')
        self.assertEqual(recorded_calls[0]['json']['variables'], {'chainId': 'chain-a'})
        self.assertEqual(recorded_calls[1]['json']['variables'], {'chainId': 'chain-a', 'from': 'hash-9', 'limit': 3})
        self.assertEqual(recorded_calls[2]['json']['variables'], {'chainId': 'chain-a', 'hash': 'hash-7'})

    async def test_fetch_block_reuses_cached_headers_for_follow_up_height(self):
        recorded_calls = []

        async def fake_post(**kwargs):
            recorded_calls.append(kwargs)
            query = kwargs['json']['query']
            variables = kwargs['json']['variables']
            if 'query TipHeader' in query:
                return FakeResponse({
                    'data': {
                        'block': {
                            'hash': 'hash-9',
                            'block': {
                                'header': {
                                    'height': 9,
                                },
                            },
                        },
                    },
                })
            if 'query BlockHeaders' in query:
                self.assertEqual(variables['from'], 'hash-9')
                return FakeResponse({
                    'data': {
                        'blocks': [
                            {
                                'hash': 'hash-9',
                                'block': {'header': {'height': 9, 'previousBlockHash': 'hash-8'}},
                            },
                            {
                                'hash': 'hash-8',
                                'block': {'header': {'height': 8, 'previousBlockHash': 'hash-7'}},
                            },
                            {
                                'hash': 'hash-7',
                                'block': {'header': {'height': 7, 'previousBlockHash': 'hash-6'}},
                            },
                        ],
                    },
                })
            if 'query BlockByHash' in query:
                return FakeResponse({
                    'data': {
                        'block': {
                            'hash': variables['hash'],
                            'block': {
                                'header': {
                                    'height': 7 if variables['hash'] == 'hash-7' else 8,
                                    'timestamp': 1234567890,
                                },
                                'body': {
                                    'messages': [],
                                    'previousMessageBlocks': {},
                                    'previousEventBlocks': {},
                                    'oracleResponses': [],
                                    'events': [],
                                    'blobs': [],
                                    'operationResults': [],
                                    'transactionMetadata': [],
                                },
                            },
                        },
                    },
                })
            raise AssertionError(f'Unexpected query: {query}')

        async_request_stub.post = fake_post
        client = LineraGraphqlChainClient('https://example.com/graphql')

        first_payload = await client.fetch_block('chain-a', 7)
        second_payload = await client.fetch_block('chain-a', 8)

        self.assertEqual(first_payload['hash'], 'hash-7')
        self.assertEqual(second_payload['hash'], 'hash-8')
        self.assertEqual(len(recorded_calls), 4)
        self.assertEqual(recorded_calls[3]['json']['variables'], {'chainId': 'chain-a', 'hash': 'hash-8'})

    async def test_fetch_block_refreshes_tip_when_target_exceeds_cached_tip_height(self):
        recorded_calls = []

        async def fake_post(**kwargs):
            recorded_calls.append(kwargs)
            query = kwargs['json']['query']
            if 'query TipHeader' in query:
                tip_height = 9 if len([call for call in recorded_calls if 'query TipHeader' in call['json']['query']]) == 1 else 11
                tip_hash = 'hash-9' if tip_height == 9 else 'hash-11'
                return FakeResponse({
                    'data': {
                        'block': {
                            'hash': tip_hash,
                            'block': {
                                'header': {
                                    'height': tip_height,
                                },
                            },
                        },
                    },
                })
            if 'query BlockHeaders' in query:
                variables = kwargs['json']['variables']
                if variables['from'] == 'hash-9':
                    return FakeResponse({
                        'data': {
                            'blocks': [
                                {'hash': 'hash-9', 'block': {'header': {'height': 9, 'previousBlockHash': 'hash-8'}}},
                                {'hash': 'hash-8', 'block': {'header': {'height': 8, 'previousBlockHash': 'hash-7'}}},
                            ],
                        },
                    })
                if variables['from'] == 'hash-11':
                    return FakeResponse({
                        'data': {
                            'blocks': [
                                {'hash': 'hash-11', 'block': {'header': {'height': 11, 'previousBlockHash': 'hash-10'}}},
                                {'hash': 'hash-10', 'block': {'header': {'height': 10, 'previousBlockHash': 'hash-9'}}},
                            ],
                        },
                    })
            if 'query BlockByHash' in query:
                variables = kwargs['json']['variables']
                return FakeResponse({
                    'data': {
                        'block': {
                            'hash': variables['hash'],
                            'block': {
                                'header': {
                                    'height': 8 if variables['hash'] == 'hash-8' else 10,
                                    'timestamp': 1234567890,
                                },
                                'body': {
                                    'messages': [],
                                    'previousMessageBlocks': {},
                                    'previousEventBlocks': {},
                                    'oracleResponses': [],
                                    'events': [],
                                    'blobs': [],
                                    'operationResults': [],
                                    'transactionMetadata': [],
                                },
                            },
                        },
                    },
                })
            raise AssertionError(f'Unexpected query: {query}')

        async_request_stub.post = fake_post
        client = LineraGraphqlChainClient('https://example.com/graphql')

        await client.fetch_block('chain-a', 8)
        payload = await client.fetch_block('chain-a', 10)

        tip_queries = [
            call for call in recorded_calls
            if 'query TipHeader' in call['json']['query']
        ]
        self.assertEqual(len(tip_queries), 2)
        self.assertEqual(payload['hash'], 'hash-10')

    async def test_fetch_block_raises_when_block_missing(self):
        async def fake_post(**kwargs):
            query = kwargs['json']['query']
            if 'query TipHeader' in query:
                return FakeResponse({
                    'data': {
                        'block': {
                            'hash': 'hash-6',
                            'block': {
                                'header': {
                                    'height': 6,
                                },
                            },
                        },
                    },
                })
            raise AssertionError('No follow-up query should be issued when target height exceeds tip')

        async_request_stub.post = fake_post
        client = LineraGraphqlChainClient('https://example.com/graphql')

        with self.assertRaisesRegex(BlockNotAvailableError, 'tip height is 6'):
            await client.fetch_block('chain-a', 7)
