import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_live_history_reconciler import PositionMetricsLiveHistoryReconciler  # noqa: E402


class PositionMetricsLiveHistoryReconcilerTest(unittest.TestCase):
    def test_reconcile_merges_live_transactions_and_recomputes_owner_basis(self):
        reconciler = PositionMetricsLiveHistoryReconciler(
            normalize_live_transaction=lambda row: dict(row),
            merge_transaction_history=lambda persisted, live: list(persisted or []) + list(live or []),
            build_transaction_gap_summary=lambda history: {
                'has_internal_gaps': False,
                'count': len(history or []),
            },
        )

        result = reconciler.reconcile(
            position={'owner': 'chain-a:owner-a'},
            payload_data={
                'latestTransactions': [
                    {
                        'transaction_id': 12,
                        'transaction_type': 'BuyToken0',
                        'from_account': 'chain-b:swapper',
                        'created_at': 3,
                    },
                    {
                        'transaction_id': 13,
                        'transaction_type': 'RemoveLiquidity',
                        'from_account': 'chain-a:owner-a',
                        'created_at': 4,
                    },
                    {
                        'transaction_id': 14,
                        'transaction_type': 'SellToken0',
                        'from_account': 'chain-b:swapper',
                        'created_at': 5,
                    },
                ],
            },
            liquidity_history=[
                {
                    'transaction_id': 11,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:owner-a',
                    'created_at': 2,
                },
            ],
            pool_transaction_history=[
                {
                    'transaction_id': 11,
                    'transaction_type': 'AddLiquidity',
                    'from_account': 'chain-a:owner-a',
                    'created_at': 2,
                },
            ],
            pool_swap_count_since_open=0,
            pool_history_gap_summary=None,
        )

        self.assertEqual(len(result['pool_transaction_history']), 4)
        self.assertEqual(
            [row['transaction_id'] for row in result['liquidity_history']],
            [11, 13],
        )
        self.assertEqual(result['pool_swap_count_since_open'], 1)
        self.assertEqual(
            result['pool_history_gap_summary'],
            {'has_internal_gaps': False, 'count': 4},
        )

    def test_reconcile_keeps_existing_histories_when_no_live_transactions(self):
        reconciler = PositionMetricsLiveHistoryReconciler(
            normalize_live_transaction=lambda row: dict(row),
            merge_transaction_history=lambda persisted, live: list(persisted or []) + list(live or []),
            build_transaction_gap_summary=lambda history: {'count': len(history or [])},
        )
        liquidity_history = [{'transaction_id': 11}]
        pool_transaction_history = [{'transaction_id': 11}]
        pool_history_gap_summary = {'has_internal_gaps': False}

        result = reconciler.reconcile(
            position={'owner': 'chain-a:owner-a'},
            payload_data={},
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=2,
            pool_history_gap_summary=pool_history_gap_summary,
        )

        self.assertIs(result['liquidity_history'], liquidity_history)
        self.assertIs(result['pool_transaction_history'], pool_transaction_history)
        self.assertEqual(result['pool_swap_count_since_open'], 2)
        self.assertIs(result['pool_history_gap_summary'], pool_history_gap_summary)


if __name__ == '__main__':
    unittest.main()
