import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_replay_entrypoint import PositionMetricsReplayEntrypoint  # noqa: E402


class PoolHistoryReplayInspectorStub:
    def __init__(self):
        self.calls = []

    def inspect(
        self,
        pool_transaction_history,
        *,
        virtual_initial_liquidity,
        swap_out_tolerance_attos,
    ):
        self.calls.append(
            (
                'inspect_pool_history_replay',
                pool_transaction_history,
                virtual_initial_liquidity,
                swap_out_tolerance_attos,
            )
        )
        return {'ok': True}


class PoolHistoryReconstructorStub:
    def __init__(self):
        self.calls = []

    def reconstruct(self, pool_transaction_history, *, virtual_initial_liquidity):
        self.calls.append(
            (
                'reconstruct',
                pool_transaction_history,
                virtual_initial_liquidity,
            )
        )
        return (['history'], ['states'], ['blocker'])


class FeeFreeOpenStateSimulatorStub:
    def __init__(self):
        self.calls = []

    def simulate(self, states, pool_transaction_history, start_index):
        self.calls.append(
            (
                'simulate',
                states,
                pool_transaction_history,
                start_index,
            )
        )
        return ({'reserve0': 11, 'reserve1': 22}, ['warn'])


class PositionMetricsReplayEntrypointTest(unittest.TestCase):
    def test_delegates_to_explicit_replay_collaborators(self):
        replay_inspector = PoolHistoryReplayInspectorStub()
        reconstructor = PoolHistoryReconstructorStub()
        fee_free_simulator = FeeFreeOpenStateSimulatorStub()
        entrypoint = PositionMetricsReplayEntrypoint(
            pool_history_replay_inspector=replay_inspector,
            pool_history_reconstructor=reconstructor,
            fee_free_open_state_simulator=fee_free_simulator,
            mint_fee_attos=lambda total_supply, reserve0, reserve1, k_last: (
                total_supply + reserve0 + reserve1 + k_last
            ),
        )

        audit = entrypoint.inspect_pool_history_replay(
            [{'transaction_id': 0}],
            virtual_initial_liquidity=False,
            swap_out_tolerance_attos=9,
        )
        reconstructed = entrypoint.reconstruct_pool_history(
            [{'transaction_id': 1}],
            virtual_initial_liquidity=True,
        )
        total_supply = entrypoint.effective_total_supply_attos_from_state(
            {
                'transaction_id': 1,
                'total_supply_after': 100,
                'reserve0_after': 10,
                'reserve1_after': 11,
                'k_last_after': 12,
            },
        )
        fee_free = entrypoint.simulate_fee_free_from_open_state(
            [{'transaction_id': 1}],
            [{'transaction_id': 2}],
            3,
        )

        self.assertEqual(audit, {'ok': True})
        self.assertEqual(reconstructed, (['history'], ['states'], ['blocker']))
        self.assertEqual(total_supply, 233)
        self.assertEqual(fee_free, ({'reserve0': 11, 'reserve1': 22}, ['warn']))
        self.assertEqual(
            replay_inspector.calls,
            [
                ('inspect_pool_history_replay', [{'transaction_id': 0}], False, 9),
            ],
        )
        self.assertEqual(
            reconstructor.calls,
            [('reconstruct', [{'transaction_id': 1}], True)],
        )
        self.assertEqual(
            fee_free_simulator.calls,
            [('simulate', [{'transaction_id': 1}], [{'transaction_id': 2}], 3)],
        )


if __name__ == '__main__':
    unittest.main()
