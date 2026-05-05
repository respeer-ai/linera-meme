import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_payload_semantic_builder import PositionMetricsPayloadSemanticBuilder  # noqa: E402


class PositionMetricsPayloadSemanticBuilderTest(unittest.TestCase):
    def test_builds_partial_metrics_owner_fee_to_and_share_ratio(self):
        builder = PositionMetricsPayloadSemanticBuilder(
            build_partial_metrics=lambda liquidity, total_supply_value, virtual_initial_liquidity: {
                'position_liquidity_live': liquidity.get('liquidity'),
                'total_supply_live': total_supply_value,
                'virtual_initial_liquidity': virtual_initial_liquidity,
                'computation_blockers': [],
            },
            account_payload_to_string=lambda account: (
                None if not isinstance(account, dict) else f"{account['chain_id']}:{account['owner']}"
            ),
        )

        result = builder.build(
            position={'owner': 'chain:owner-a'},
            payload_data={
                'pool': {'fee_to': {'chain_id': 'chain', 'owner': 'owner-a'}},
                'totalSupply': '10',
                'virtualInitialLiquidity': True,
                'liquidity': {'liquidity': '4', 'amount0': '8', 'amount1': '12'},
            },
        )

        self.assertEqual(result['position_liquidity_live'], '4')
        self.assertEqual(result['total_supply_live'], '10')
        self.assertTrue(result['virtual_initial_liquidity'])
        self.assertTrue(result['owner_is_fee_to'])
        self.assertEqual(result['exact_share_ratio'], '0.4')

    def test_builds_partial_metrics_owner_fee_to_from_public_account_string(self):
        builder = PositionMetricsPayloadSemanticBuilder(
            build_partial_metrics=lambda liquidity, total_supply_value, virtual_initial_liquidity: {
                'position_liquidity_live': liquidity.get('liquidity'),
                'total_supply_live': total_supply_value,
                'virtual_initial_liquidity': virtual_initial_liquidity,
                'computation_blockers': [],
            },
            account_payload_to_string=lambda account: account if isinstance(account, str) else None,
        )

        result = builder.build(
            position={'owner': 'chain:owner-a'},
            payload_data={
                'pool': {'fee_to': 'chain:owner-a'},
                'totalSupply': '10',
                'virtualInitialLiquidity': False,
                'liquidity': {'liquidity': '4', 'amount0': '8', 'amount1': '12'},
            },
        )

        self.assertTrue(result['owner_is_fee_to'])
