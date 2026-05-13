import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_fee_free_open_state_simulator import PositionMetricsFeeFreeOpenStateSimulator  # noqa: E402


class PositionMetricsFeeFreeOpenStateSimulatorTest(unittest.TestCase):
    def test_simulate_applies_swaps_after_open(self):
        simulator = PositionMetricsFeeFreeOpenStateSimulator(
            to_attos=lambda value: 0 if value is None else int(value),
        )

        state, blockers = simulator.simulate(
            [{'reserve0_after': 100, 'reserve1_after': 200}],
            [
                {'transaction_type': 'AddLiquidity'},
                {'transaction_type': 'BuyToken0', 'amount_1_in': 20},
                {'transaction_type': 'SellToken0', 'amount_0_in': 10},
            ],
            0,
        )

        self.assertEqual(blockers, [])
        self.assertEqual(state['reserve0'], 101)
        self.assertEqual(state['reserve1'], 199)

    def test_simulate_reports_liquidity_change_blocker(self):
        simulator = PositionMetricsFeeFreeOpenStateSimulator(
            to_attos=lambda value: 0 if value is None else int(value),
        )

        state, blockers = simulator.simulate(
            [{'reserve0_after': 100, 'reserve1_after': 200}],
            [
                {'transaction_type': 'AddLiquidity'},
                {'transaction_type': 'RemoveLiquidity'},
            ],
            0,
        )

        self.assertEqual(state['reserve0'], 100)
        self.assertEqual(state['reserve1'], 200)
        self.assertEqual(blockers, ['pool_has_liquidity_changes_after_position_open'])


if __name__ == '__main__':
    unittest.main()
