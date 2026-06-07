import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.business_freshness import BusinessFreshnessReadModel  # noqa: E402


class FakeRawRepository:
    def __init__(self, rows):
        self.rows = rows

    def list_chain_cursors(self, chain_ids=(), limit=200):
        return [row for row in self.rows if not chain_ids or row['chain_id'] in chain_ids][:limit]


class FakeProcessingCursorRepository:
    def __init__(self, rows):
        self.rows = rows

    def list_cursors(self, limit=200):
        return self.rows[:limit]


class FakeSettledTradeProjectionRepository:
    def __init__(self, watermark_ms=None):
        self.watermark_ms = watermark_ms

    def load_pool_market_watermark_ms(self, pool_application):
        return self.watermark_ms


class BusinessFreshnessReadModelTest(unittest.TestCase):
    def test_reports_l1_unavailable_when_chain_cursor_is_missing(self):
        snapshot = self._snapshot(raw_rows=[])

        self.assertEqual(snapshot['status'], 'l1_unavailable')
        self.assertEqual(snapshot['reason_codes'], ['l1_cursor_missing'])

    def test_reports_normalization_stale_when_l2_is_behind_l1(self):
        snapshot = self._snapshot(l1_height=10, l2_sequence=9, l3_sequence=9)

        self.assertEqual(snapshot['status'], 'normalization_stale')
        self.assertEqual(snapshot['reason_codes'], ['l2_behind_l1'])

    def test_reports_market_derivation_stale_when_l3_is_behind_l2(self):
        snapshot = self._snapshot(l1_height=10, l2_sequence=10, l3_sequence=9)

        self.assertEqual(snapshot['status'], 'market_derivation_stale')
        self.assertEqual(snapshot['reason_codes'], ['l3_behind_l2'])

    def test_reports_product_read_stale_when_pool_watermark_is_missing(self):
        snapshot = self._snapshot(l1_height=10, l2_sequence=10, l3_sequence=10, pool_application='pool-app')

        self.assertEqual(snapshot['status'], 'product_read_stale')
        self.assertEqual(snapshot['reason_codes'], ['product_watermark_missing'])

    def test_reports_fresh_when_watermarks_are_aligned(self):
        snapshot = self._snapshot(
            l1_height=10,
            l2_sequence=10,
            l3_sequence=10,
            pool_application='pool-app',
            product_watermark_ms=1234,
        )

        self.assertEqual(snapshot['status'], 'fresh')
        self.assertEqual(snapshot['reason_codes'], [])
        self.assertEqual(snapshot['checked_at_ms'], 42)

    def _snapshot(
        self,
        *,
        raw_rows=None,
        l1_height=1,
        l2_sequence=1,
        l3_sequence=1,
        pool_application=None,
        product_watermark_ms=None,
    ):
        if raw_rows is None:
            raw_rows = [{'chain_id': 'chain-a', 'last_finalized_height': l1_height}]
        cursors = [
            {'cursor_name': 'layer2_normalizer', 'last_sequence': l2_sequence},
            {'cursor_name': 'layer3_market_deriver', 'last_sequence': l3_sequence},
        ]
        read_model = BusinessFreshnessReadModel(
            raw_repository=FakeRawRepository(raw_rows),
            processing_cursor_repository=FakeProcessingCursorRepository(cursors),
            settled_trade_projection_repository=FakeSettledTradeProjectionRepository(product_watermark_ms),
            clock_ms=lambda: 42,
        )
        return read_model.load_snapshot(chain_id='chain-a', pool_application=pool_application)


if __name__ == '__main__':
    unittest.main()
