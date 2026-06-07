import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from business_freshness_service import BusinessFreshnessService  # noqa: E402
from business_freshness_snapshot_store import BusinessFreshnessSnapshotStore  # noqa: E402


class FakeReadModel:
    def __init__(self):
        self.calls = []

    def load_snapshot(self, *, chain_id=None, pool_application=None):
        self.calls.append({'chain_id': chain_id, 'pool_application': pool_application})
        return {
            'scope': {'chain_id': chain_id, 'pool_application': pool_application},
            'status': 'fresh',
            'reason_codes': [],
        }


class BusinessFreshnessServiceTest(unittest.TestCase):
    def test_check_stores_latest_snapshot(self):
        service = self._service()

        snapshot = service.check(chain_id='chain-a', trigger='chain_catch_up')

        self.assertEqual(snapshot['scope_key'], 'chain:chain-a')
        self.assertEqual(snapshot['trigger'], 'chain_catch_up')
        self.assertEqual(service.get_latest(chain_id='chain-a'), snapshot)

    def test_pool_scope_takes_priority_over_chain_scope(self):
        service = self._service()

        snapshot = service.check(chain_id='chain-a', pool_application='pool-app')

        self.assertEqual(snapshot['scope_key'], 'pool:pool-app')
        self.assertIsNone(service.get_latest(chain_id='chain-a'))

    def test_debug_payload_returns_computed_and_previous_latest(self):
        service = self._service()
        previous = service.check(chain_id='chain-a', trigger='event')

        payload = service.get_debug_payload(chain_id='chain-a')

        self.assertEqual(payload['latest'], previous)
        self.assertEqual(payload['computed']['trigger'], 'debug_request')

    def test_calls_snapshot_update_callback(self):
        updates = []
        service = self._service(on_snapshot_updated=updates.append)

        snapshot = service.check(chain_id='chain-a')

        self.assertEqual(updates, [snapshot])

    def test_runs_without_snapshot_update_callback(self):
        service = self._service()

        snapshot = service.check()

        self.assertEqual(snapshot['scope_key'], 'global')

    def _service(self, *, on_snapshot_updated=None):
        return BusinessFreshnessService(
            read_model=FakeReadModel(),
            snapshot_store=BusinessFreshnessSnapshotStore(),
            on_snapshot_updated=on_snapshot_updated,
        )


if __name__ == '__main__':
    unittest.main()
