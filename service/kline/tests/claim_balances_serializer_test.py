import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.serializers.claim_balances import ClaimBalancesSerializer  # noqa: E402


class ClaimBalancesSerializerTest(unittest.TestCase):
    def test_filters_claim_balance_fields(self):
        payload = {
            'owner': 'owner-a',
            'balances': [{
                'pool_application_id': 'pool-app',
                'execution_chain_id': 'pool-chain',
                'token': 'native',
                'owner': 'owner-a',
                'claimable_amount': '7',
                'claiming_amount': '3',
                'projection_status': 'incomplete',
                'diagnostics': {'incomplete_count': 2},
                'latest_block_height': 11,
                'latest_transaction_index': 2,
                'latest_message_index': 1,
                'internal': 'ignored',
            }],
        }

        serialized = ClaimBalancesSerializer().serialize_claim_balances(payload)

        self.assertEqual(serialized['owner'], 'owner-a')
        self.assertNotIn('internal', serialized['balances'][0])
        self.assertEqual(serialized['balances'][0]['claimable_amount'], '7')
        self.assertEqual(serialized['balances'][0]['claiming_amount'], '3')
        self.assertEqual(serialized['balances'][0]['projection_status'], 'incomplete')
        self.assertEqual(serialized['balances'][0]['diagnostics'], {'incomplete_count': 2})


if __name__ == '__main__':
    unittest.main()
