import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


async_request_stub = types.ModuleType('async_request')
async_request_stub.post = object()
sys.modules.setdefault('async_request', async_request_stub)


from position_metrics_bootstrap import PositionMetricsBootstrap  # noqa: E402
from position_metrics_public_api import PositionMetricsPublicApi  # noqa: E402
from position_metrics_replay_entrypoint import PositionMetricsReplayEntrypoint  # noqa: E402


class PositionMetricsBootstrapTest(unittest.TestCase):
    def test_bootstrap_builds_public_and_replay_boundaries_without_assembly_shell(self):
        bootstrap = PositionMetricsBootstrap()

        public_api = bootstrap.public_api()
        replay_entrypoint = bootstrap.replay_entrypoint()
        replay_inspector = bootstrap.pool_history_replay_inspector()
        reconstructor = bootstrap.pool_history_reconstructor()
        fee_free_simulator = bootstrap.fee_free_open_state_simulator()

        self.assertIsInstance(public_api, PositionMetricsPublicApi)
        self.assertIsInstance(replay_entrypoint, PositionMetricsReplayEntrypoint)
        self.assertIs(replay_entrypoint.pool_history_replay_inspector, replay_inspector)
        self.assertIs(replay_entrypoint.pool_history_reconstructor, reconstructor)
        self.assertIs(replay_entrypoint.fee_free_open_state_simulator, fee_free_simulator)
        self.assertEqual(
            replay_entrypoint.effective_total_supply_attos_from_state(
                {
                    'total_supply_after': 100,
                    'reserve0_after': 10,
                    'reserve1_after': 20,
                    'k_last_after': 5,
                }
            ),
            100 + bootstrap.mint_fee_attos(100, 10, 20, 5),
        )
        self.assertIs(public_api.replay_entrypoint, replay_entrypoint)

    def test_bootstrap_gap_summary_explicitly_treats_transaction_ids_as_non_contiguous(self):
        bootstrap = PositionMetricsBootstrap()

        summary = bootstrap.build_transaction_gap_summary(
            [
                {'transaction_id': 10},
                {'transaction_id': 12},
                {'transaction_id': 14},
            ],
            start_id=9,
            end_id=20,
        )

        self.assertEqual(
            summary,
            {
                'has_internal_gaps': False,
                'start_id': 10,
                'end_id': 14,
                'missing_count': 0,
                'missing_ids_sample': [],
                'basis': 'accepted_transaction_ids_are_not_required_to_be_contiguous',
            },
        )


if __name__ == '__main__':
    unittest.main()
