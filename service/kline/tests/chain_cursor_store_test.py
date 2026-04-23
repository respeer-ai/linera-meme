import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from ingestion.chain_cursor_store import ChainCursorStore  # noqa: E402


class ChainCursorStoreTest(unittest.TestCase):
    class FakeRawRepository:
        def __init__(self, row=None):
            self.row = row
            self.calls = []

        def load_chain_cursor(self, chain_id: str):
            self.calls.append(chain_id)
            return self.row

    def test_load_returns_default_cursor_when_row_missing(self):
        repository = self.FakeRawRepository(row=None)
        store = ChainCursorStore(repository)

        cursor = store.load('chain-a')

        self.assertEqual(repository.calls, ['chain-a'])
        self.assertEqual(cursor.chain_id, 'chain-a')
        self.assertIsNone(cursor.last_finalized_height)
        self.assertIsNone(cursor.last_finalized_block_hash)

    def test_load_maps_repository_row_to_chain_cursor(self):
        repository = self.FakeRawRepository(row={
            'chain_id': 'chain-a',
            'last_finalized_height': 7,
            'last_finalized_block_hash': 'hash-7',
        })
        store = ChainCursorStore(repository)

        cursor = store.load('chain-a')

        self.assertEqual(cursor.chain_id, 'chain-a')
        self.assertEqual(cursor.last_finalized_height, 7)
        self.assertEqual(cursor.last_finalized_block_hash, 'hash-7')
