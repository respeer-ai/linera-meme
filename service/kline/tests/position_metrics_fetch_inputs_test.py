import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_fetch_inputs import PositionMetricsFetchInputs  # noqa: E402
from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot  # noqa: E402
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot  # noqa: E402
from query.read_models.position_metrics_replay_bundle import PositionMetricsReplayBundle  # noqa: E402
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402


class PositionMetricsFetchInputsTest(unittest.TestCase):
    def test_builds_fast_path_kwargs_from_loaded_inputs(self):
        replay_bundle_calls = []

        fetch_inputs = PositionMetricsFetchInputs(
            position={'owner': 'chain:owner-a'},
            payload={'data': {}},
            snapshot_inputs=PositionMetricsSnapshotInputs(
                {
                    'position_basis_snapshot': {'basis_transaction_id': 11},
                    'pool_state_snapshot': {'last_transaction_id': 12},
                }
            ),
            replay_bundle_loader=lambda: replay_bundle_calls.append('load') or object(),
        )

        kwargs = fetch_inputs.fast_path_kwargs()
        self.assertEqual(kwargs['position'], {'owner': 'chain:owner-a'})
        self.assertEqual(kwargs['payload'], {'data': {}})
        self.assertIsInstance(kwargs['position_basis_snapshot'], PositionMetricsPositionBasisSnapshot)
        self.assertIsInstance(kwargs['pool_state_snapshot'], PositionMetricsPoolStateSnapshot)
        self.assertEqual(kwargs['position_basis_snapshot'].raw(), {'basis_transaction_id': 11})
        self.assertEqual(kwargs['pool_state_snapshot'].raw(), {'last_transaction_id': 12})
        self.assertEqual(replay_bundle_calls, [])

    def test_builds_enrich_kwargs_and_replay_summary(self):
        class FakeReplayBundle:
            def replay_summary(self):
                return {'latest_pool_transaction_id': 12}

        replay_bundle = FakeReplayBundle()
        replay_bundle_calls = []
        fetch_inputs = PositionMetricsFetchInputs(
            position={'owner': 'chain:owner-a'},
            payload={'data': {}},
            snapshot_inputs=PositionMetricsSnapshotInputs(
                {
                    'position_basis_snapshot': {'basis_transaction_id': 11},
                    'pool_state_snapshot': {'last_transaction_id': 12},
                }
            ),
            replay_bundle_loader=lambda: replay_bundle_calls.append('load') or PositionMetricsReplayBundle(
                {
                    'liquidity_history': [],
                    'pool_transaction_history': [],
                    'pool_swap_count_since_open': 0,
                    'pool_history_gap_summary': {},
                    'replay_summary': replay_bundle.replay_summary(),
                }
            ),
        )

        enrich_kwargs = fetch_inputs.enrich_kwargs()
        self.assertIs(enrich_kwargs['replay_bundle'], fetch_inputs.replay_bundle())
        self.assertIsInstance(enrich_kwargs['position_basis_snapshot'], PositionMetricsPositionBasisSnapshot)
        self.assertIsInstance(enrich_kwargs['pool_state_snapshot'], PositionMetricsPoolStateSnapshot)
        self.assertEqual(enrich_kwargs['position_basis_snapshot'].raw(), {'basis_transaction_id': 11})
        self.assertEqual(enrich_kwargs['pool_state_snapshot'].raw(), {'last_transaction_id': 12})
        self.assertEqual(
            fetch_inputs.replay_summary().as_dict(),
            {'latest_pool_transaction_id': 12},
        )
        self.assertEqual(replay_bundle_calls, ['load'])


if __name__ == '__main__':
    unittest.main()
