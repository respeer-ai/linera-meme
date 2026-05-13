import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_pool_state_snapshot import (  # noqa: E402
    PositionMetricsPoolStateSnapshot,
)


class PositionMetricsPoolStateSnapshotTest(unittest.TestCase):
    def test_exposes_named_pool_state_fields(self):
        snapshot = PositionMetricsPoolStateSnapshot(
            {
                'fee_free_reserve_0': '90',
                'fee_free_reserve_1': '190',
                'last_transaction_id': 12,
                'last_trade_time_ms': 1300,
                'last_liquidity_event_time_ms': 1250,
                'fee_free_basis_transaction_id': 11,
                'fee_free_basis_time_ms': 1200,
            }
        )

        self.assertEqual(snapshot.fee_free_reserve_0(), '90')
        self.assertEqual(snapshot.fee_free_reserve_1(), '190')
        self.assertEqual(snapshot.last_transaction_id(), 12)
        self.assertEqual(snapshot.last_trade_time_ms(), 1300)
        self.assertEqual(snapshot.last_liquidity_event_time_ms(), 1250)
        self.assertEqual(snapshot.fee_free_basis_transaction_id(), 11)
        self.assertEqual(snapshot.fee_free_basis_time_ms(), 1200)
        self.assertEqual(
            snapshot.shadow_latest_dict(),
            {
                'latest_pool_transaction_id': 12,
                'latest_pool_trade_time_ms': 1300,
                'latest_pool_liquidity_event_time_ms': 1250,
            },
        )
        self.assertEqual(
            snapshot.summary_dict(),
            {
                'last_transaction_id': 12,
                'last_trade_time_ms': 1300,
                'last_liquidity_event_time_ms': 1250,
            },
        )
        self.assertEqual(
            snapshot.raw(),
            {
                'fee_free_reserve_0': '90',
                'fee_free_reserve_1': '190',
                'last_transaction_id': 12,
                'last_trade_time_ms': 1300,
                'last_liquidity_event_time_ms': 1250,
                'fee_free_basis_transaction_id': 11,
                'fee_free_basis_time_ms': 1200,
            },
        )
