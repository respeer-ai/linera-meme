import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from account_codec import AccountCodec  # noqa: E402


class AccountCodecTest(unittest.TestCase):
    def test_public_account_from_payload_accepts_protocol_account(self):
        codec = AccountCodec()
        owner = '0xd4a2fd162d513d0073b5342f7e3fa50c096fe8bed72fa1f5b06dd1b01f951985'

        self.assertEqual(
            codec.public_account_from_payload({'chain_id': 'chain-a', 'owner': owner}),
            f'{owner}@chain-a',
        )
        self.assertEqual(
            codec.public_account_from_payload(f'{owner}@chain-a'),
            f'{owner}@chain-a',
        )
        self.assertEqual(
            codec.public_account_from_payload('chain-a'),
            '0x00@chain-a',
        )

    def test_public_and_settled_owner_round_trip(self):
        codec = AccountCodec()
        owner = '0xd4a2fd162d513d0073b5342f7e3fa50c096fe8bed72fa1f5b06dd1b01f951985'

        settled = codec.settled_owner_from_public_account(f'{owner}@chain-a')

        self.assertEqual(settled, f'{owner}@chain-a')
        self.assertEqual(codec.public_account_from_settled_owner(settled), f'{owner}@chain-a')

    def test_payload_from_public_account_builds_account_dict(self):
        codec = AccountCodec()
        owner = '0xd4a2fd162d513d0073b5342f7e3fa50c096fe8bed72fa1f5b06dd1b01f951985'

        self.assertEqual(
            codec.payload_from_public_account(f'{owner}@chain-a'),
            {'chain_id': 'chain-a', 'owner': owner},
        )

    def test_owner_requires_protocol_prefix(self):
        codec = AccountCodec()
        owner = 'd4a2fd162d513d0073b5342f7e3fa50c096fe8bed72fa1f5b06dd1b01f951985'

        self.assertIsNone(codec.payload_from_public_account(f'{owner}@chain-a'))
        self.assertIsNone(codec.payload_from_public_account(f'chain-a:{owner}'))

    def test_application_id_from_account_removes_protocol_owner_prefix(self):
        codec = AccountCodec()
        application_id = 'd4a2fd162d513d0073b5342f7e3fa50c096fe8bed72fa1f5b06dd1b01f951985'

        self.assertEqual(
            codec.application_id_from_account(f'0x{application_id}@chain-a'),
            application_id,
        )


if __name__ == '__main__':
    unittest.main()
