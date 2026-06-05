import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.claim_balances import ClaimBalancesReadModel  # noqa: E402


class ClaimBalancesReadModelTest(unittest.TestCase):
    class FakeRepository:
        def __init__(self, rows):
            self.rows = rows
            self.calls = []

        def get_claim_balances(self, **kwargs):
            self.calls.append(dict(kwargs))
            return self.rows

    def test_reads_claim_balances_from_projection_repository(self):
        repository = self.FakeRepository([{'token': 'native', 'claimable_amount': '7'}])

        payload = ClaimBalancesReadModel(repository).get_claim_balances(owner='owner-a')

        self.assertEqual(payload, {
            'owner': 'owner-a',
            'balances': [{'token': 'native', 'claimable_amount': '7'}],
        })
        self.assertEqual(repository.calls, [{'owner': 'owner-a'}])


if __name__ == '__main__':
    unittest.main()
