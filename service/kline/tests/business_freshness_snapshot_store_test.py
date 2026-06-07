import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from business_freshness_snapshot_store import BusinessFreshnessSnapshotStore  # noqa: E402


class BusinessFreshnessSnapshotStoreTest(unittest.TestCase):
    def test_stores_and_reads_latest_snapshot_by_scope(self):
        store = BusinessFreshnessSnapshotStore()

        store.set_latest('chain:chain-a', {'status': 'fresh'})

        self.assertEqual(store.get_latest('chain:chain-a'), {'status': 'fresh'})

    def test_overwrites_existing_scope(self):
        store = BusinessFreshnessSnapshotStore()

        store.set_latest('pool:pool-a', {'status': 'normalization_stale'})
        store.set_latest('pool:pool-a', {'status': 'fresh'})

        self.assertEqual(store.get_latest('pool:pool-a'), {'status': 'fresh'})

    def test_missing_scope_returns_none(self):
        store = BusinessFreshnessSnapshotStore()

        self.assertIsNone(store.get_latest('global'))

    def test_lists_latest_snapshots(self):
        store = BusinessFreshnessSnapshotStore()
        store.set_latest('global', {'status': 'upstream_idle'})
        store.set_latest('chain:chain-a', {'status': 'fresh'})

        self.assertEqual(
            store.list_latest(),
            {
                'global': {'status': 'upstream_idle'},
                'chain:chain-a': {'status': 'fresh'},
            },
        )

    def test_returns_copies(self):
        store = BusinessFreshnessSnapshotStore()
        snapshot = store.set_latest('global', {'status': 'fresh'})
        snapshot['status'] = 'mutated'

        loaded = store.get_latest('global')
        loaded['status'] = 'mutated-again'

        self.assertEqual(store.get_latest('global'), {'status': 'fresh'})


if __name__ == '__main__':
    unittest.main()
