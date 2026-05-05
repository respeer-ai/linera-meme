import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from account_codec import AccountCodec  # noqa: E402


class AccountCodecTest(unittest.TestCase):
    def test_public_account_from_payload_accepts_dict_and_strings(self):
        codec = AccountCodec()

        self.assertEqual(
            codec.public_account_from_payload({'chain_id': 'chain-a', 'owner': 'owner-a'}),
            'chain-a:owner-a',
        )
        self.assertEqual(
            codec.public_account_from_payload('chain-a:owner-a'),
            'chain-a:owner-a',
        )
        self.assertEqual(
            codec.public_account_from_payload('owner-a@chain-a'),
            'chain-a:owner-a',
        )

    def test_public_and_settled_owner_round_trip(self):
        codec = AccountCodec()

        settled = codec.settled_owner_from_public_account('chain-a:owner-a')

        self.assertEqual(settled, 'owner-a@chain-a')
        self.assertEqual(codec.public_account_from_settled_owner(settled), 'chain-a:owner-a')

    def test_payload_from_public_account_builds_account_dict(self):
        codec = AccountCodec()

        self.assertEqual(
            codec.payload_from_public_account('chain-a:owner-a'),
            {'chain_id': 'chain-a', 'owner': 'owner-a'},
        )
        self.assertIsNone(codec.payload_from_public_account('invalid-owner'))


if __name__ == '__main__':
    unittest.main()
