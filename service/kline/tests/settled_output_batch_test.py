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

    def test_reports_affected_pools_and_positions(self):
        batch = SettledOutputBatch(
            outputs=[
                {
                    'settled_output_type': 'settled_trade',
                    'pool_application_id': 'chain-a:pool-app',
                    'pool_chain_id': 'chain-a',
                },
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': 'chain-a:pool-app',
                    'pool_chain_id': 'chain-a',
                    'owner': 'owner-user@chain-user',
                },
                {
                    'settled_output_type': 'settled_liquidity_change',
                    'pool_application_id': 'chain-b:pool-app',
                    'owner': 'chain-user:owner-direct',
                },
            ]
        )

        self.assertEqual(
            batch.affected_pools(),
            [
                ('chain-a:pool-app', 'chain-a'),
                ('chain-b:pool-app', None),
            ],
        )
        self.assertEqual(
            batch.affected_positions(),
            [
                ('chain-user:owner-direct', 'chain-b:pool-app', None),
                ('chain-user:owner-user', 'chain-a:pool-app', 'chain-a'),
            ],
        )
