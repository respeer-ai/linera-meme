import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from ingestion.block_parser import LayerOneBlockParser  # noqa: E402


class BlockParserTest(unittest.TestCase):
    def test_parse_normalizes_layer1_block_shape(self):
        parser = LayerOneBlockParser()

        block = parser.parse('chain-a', 7, {
            'hash': 'hash-7',
            'timestamp_ms': 123456,
            'incoming_bundles': [
                {
                    'origin_chain_id': 'chain-b',
                    'posted_messages': [{'raw_message_bytes': b'hello'}],
                },
            ],
            'operations': [{'raw_operation_bytes': b'op'}],
            'outgoing_messages': [{'destination_chain_id': 'chain-c', 'raw_message_bytes': b'out'}],
            'events': [{'stream_id': 'stream-1', 'raw_event_bytes': b'evt'}],
            'oracle_responses': [{'response_type': 'blob', 'raw_response_bytes': b'oracle'}],
        })

        self.assertEqual(block['chain_id'], 'chain-a')
        self.assertEqual(block['height'], 7)
        self.assertEqual(block['block_hash'], 'hash-7')
        self.assertEqual(block['incoming_bundle_count'], 1)
        self.assertEqual(block['operation_count'], 1)
        self.assertEqual(block['message_count'], 1)
        self.assertEqual(block['event_count'], 1)
        self.assertEqual(block['incoming_bundles'][0]['posted_messages'][0]['message_index'], 0)

    def test_parse_requires_block_hash(self):
        parser = LayerOneBlockParser()

        with self.assertRaisesRegex(ValueError, 'Missing block hash'):
            parser.parse('chain-a', 7, {'timestamp_ms': 1})

    def test_parse_normalizes_confirmed_block_graphql_shape(self):
        parser = LayerOneBlockParser()

        block = parser.parse('chain-a', 7, {
            'hash': 'hash-7',
            'block': {
                'header': {
                    'height': 7,
                    'timestamp': 1694097511817833,
                    'epoch': '0',
                    'stateHash': 'state-7',
                    'previousBlockHash': 'hash-6',
                    'authenticatedSigner': 'owner-a',
                },
                'body': {
                    'messages': [[
                        {
                            'destination': 'chain-z',
                            'authenticatedSigner': 'owner-a',
                            'grant': '0.01',
                            'kind': 'Tracked',
                            'message': {
                                'User': {
                                    'application_id': 'app-out',
                                    'bytes': '6869',
                                },
                            },
                        },
                    ]],
                    'events': [[
                        {
                            'streamId': {
                                'applicationId': 'app-stream',
                                'streamName': 'fills',
                            },
                            'index': 4,
                            'value': [1, 2, 3],
                        },
                    ]],
                    'oracleResponses': [[{'Blob': {'blobHash': 'blob-1'}}]],
                    'blobs': [[{'id': 'blob-a'}]],
                    'transactionMetadata': [
                        {
                            'transactionType': 'ReceiveMessages',
                            'incomingBundle': {
                                'origin': {
                                    'medium': 'Direct',
                                    'sender': 'chain-b',
                                },
                                'action': 'Accept',
                                'bundle': {
                                    'height': 6,
                                    'timestamp': 1694097510206912,
                                    'certificateHash': 'cert-6',
                                    'transactionIndex': 2,
                                    'messages': [
                                        {
                                            'authenticatedSigner': 'owner-b',
                                            'grant': '0.02',
                                            'refundGrantTo': 'refund-a',
                                            'kind': 'Tracked',
                                            'index': 3,
                                            'message': {'System': {'Withdraw': {'owner': 'o', 'amount': '1', 'recipient': 'r'}}},
                                            'messageMetadata': {
                                                'messageType': 'System',
                                                'applicationId': None,
                                                'userBytesHex': None,
                                                'systemMessage': {
                                                    'systemMessageType': 'Withdraw',
                                                    'withdraw': {
                                                        'owner': 'o',
                                                        'amount': '1',
                                                        'recipient': 'r',
                                                    },
                                                },
                                            },
                                        },
                                    ],
                                },
                            },
                            'operation': None,
                        },
                        {
                            'transactionType': 'ExecuteOperation',
                            'incomingBundle': None,
                            'operation': {
                                'operationType': 'User',
                                'applicationId': 'app-op',
                                'userBytesHex': '6f70',
                                'systemOperation': None,
                            },
                        },
                    ],
                },
            },
        })

        self.assertEqual(block['block_hash'], 'hash-7')
        self.assertEqual(block['timestamp_ms'], 1694097511817)
        self.assertEqual(block['incoming_bundle_count'], 1)
        self.assertEqual(block['operation_count'], 1)
        self.assertEqual(block['message_count'], 1)
        self.assertEqual(block['event_count'], 1)
        self.assertEqual(block['blob_count'], 1)
        self.assertEqual(block['incoming_bundles'][0]['origin_chain_id'], 'chain-b')
        self.assertEqual(block['incoming_bundles'][0]['posted_messages'][0]['system_message_type'], 'Withdraw')
        self.assertEqual(block['operations'][0]['application_id'], 'app-op')
        self.assertEqual(block['operations'][0]['raw_operation_bytes'], b'op')
        self.assertEqual(block['outgoing_messages'][0]['application_id'], 'app-out')
        self.assertEqual(
            block['outgoing_messages'][0]['raw_message_bytes'],
            b'{"User":{"application_id":"app-out","bytes":"6869"}}',
        )
        self.assertEqual(block['events'][0]['stream_id'], 'app-stream:fills')
        self.assertEqual(block['oracle_responses'][0]['response_type'], 'Blob')
