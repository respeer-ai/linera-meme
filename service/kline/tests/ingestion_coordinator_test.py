import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from ingestion.coordinator import IngestionCoordinator  # noqa: E402
from ingestion.cursors import ChainCursor  # noqa: E402


class IngestionCoordinatorTest(unittest.IsolatedAsyncioTestCase):
    class FakeChainClient:
        def __init__(self, block=None, error=None):
            self.block = block or {}
            self.error = error
            self.calls = []

        async def fetch_block(self, chain_id: str, height: int) -> dict:
            self.calls.append((chain_id, height))
            if self.error is not None:
                raise self.error
            return dict(self.block)

    class FakeRawRepository:
        def __init__(self):
            self.calls = []

        def mark_attempt(self, chain_id: str, height: int) -> None:
            self.calls.append(('mark_attempt', chain_id, height))

        def ingest_block(self, block: dict, mode: str = 'live') -> dict:
            self.calls.append(('ingest_block', dict(block), mode))
            return {
                'chain_id': block['chain_id'],
                'height': block['height'],
                'block_hash': block['block_hash'],
                'ingest_status': 'ingested',
                'cursor_advanced': True,
            }

        def mark_failure(self, chain_id: str, height: int, error_text: str) -> None:
            self.calls.append(('mark_failure', chain_id, height, error_text))

    async def test_ingest_from_cursor_fetches_next_height_and_persists_block(self):
        chain_client = self.FakeChainClient(block={
            'chain_id': 'chain-a',
            'height': 6,
            'block_hash': 'hash-6',
            'timestamp_ms': 123456,
        })
        raw_repository = self.FakeRawRepository()
        coordinator = IngestionCoordinator(chain_client=chain_client, raw_repository=raw_repository)

        result = await coordinator.ingest_from_cursor(
            ChainCursor(chain_id='chain-a', last_finalized_height=5),
            mode='catch_up',
        )

        self.assertEqual(chain_client.calls, [('chain-a', 6)])
        self.assertEqual(raw_repository.calls[0], ('mark_attempt', 'chain-a', 6))
        self.assertEqual(raw_repository.calls[1][0], 'ingest_block')
        self.assertEqual(result['block_hash'], 'hash-6')

    async def test_ingest_from_cursor_marks_failure_when_fetch_fails(self):
        chain_client = self.FakeChainClient(error=RuntimeError('rpc failed'))
        raw_repository = self.FakeRawRepository()
        coordinator = IngestionCoordinator(chain_client=chain_client, raw_repository=raw_repository)

        with self.assertRaisesRegex(RuntimeError, 'rpc failed'):
            await coordinator.ingest_from_cursor(
                ChainCursor(chain_id='chain-a', last_finalized_height=None),
            )

        self.assertEqual(raw_repository.calls[0], ('mark_attempt', 'chain-a', 0))
        self.assertEqual(raw_repository.calls[1], ('mark_failure', 'chain-a', 0, 'rpc failed'))
