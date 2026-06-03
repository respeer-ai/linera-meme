import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from market.settled_output_batch import SettledOutputBatch  # noqa: E402


class SettledOutputBatchTest(unittest.TestCase):
    def test_partitions_trades_and_liquidity_changes(self):
        batch = SettledOutputBatch(
            outputs=[
                {'settled_output_type': 'settled_trade', 'settled_trade_id': 'trade-1'},
                {'settled_output_type': 'settled_liquidity_change', 'settled_liquidity_change_id': 'liq-1'},
                {'settled_output_type': 'claim_balance_delta', 'claim_balance_delta_id': 'claim-1'},
                {'settled_output_type': 'claim_balance_diagnostic', 'claim_balance_diagnostic_id': 'diag-1'},
                {'settled_output_type': 'unknown', 'id': 'ignored'},
            ]
        )

        self.assertEqual(
            batch.trades(),
            [{'settled_output_type': 'settled_trade', 'settled_trade_id': 'trade-1'}],
        )
        self.assertEqual(
            batch.liquidity_changes(),
            [{'settled_output_type': 'settled_liquidity_change', 'settled_liquidity_change_id': 'liq-1'}],
        )
        self.assertEqual(
            batch.claim_balance_deltas(),
            [{'settled_output_type': 'claim_balance_delta', 'claim_balance_delta_id': 'claim-1'}],
        )
        self.assertEqual(
            batch.claim_balance_diagnostics(),
            [{'settled_output_type': 'claim_balance_diagnostic', 'claim_balance_diagnostic_id': 'diag-1'}],
        )

    def test_reports_affected_pools_and_positions(self):
        batch = SettledOutputBatch(
            outputs=[
                {
                    'settled_output_type': 'settled_trade',
                    'pool_application_id': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a',
                    'pool_chain_id': 'chain-a',
                },
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a',
                    'pool_chain_id': 'chain-a',
                    'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user',
                },
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc@chain-b',
                    'owner': '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-user',
                },
            ]
        )

        self.assertEqual(
            batch.affected_pools(),
            [
                ('0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a', 'chain-a'),
                ('0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc@chain-b', None),
            ],
        )
        self.assertEqual(
            batch.affected_positions(),
            [
                (
                    '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-user',
                    '0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb@chain-a',
                    'chain-a',
                ),
                (
                    '0xdddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddddd@chain-user',
                    '0xcccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc@chain-b',
                    None,
                ),
            ],
        )
