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
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402


class PositionMetricsFetchInputsTest(unittest.TestCase):
    def test_builds_fast_path_kwargs_from_loaded_inputs(self):
        fetch_inputs = PositionMetricsFetchInputs(
            position={'owner': 'chain:owner-a'},
            payload={'data': {}},
            snapshot_inputs=PositionMetricsSnapshotInputs(
                {
                    'position_basis_snapshot': {'basis_transaction_id': 11},
                    'pool_state_snapshot': {'last_transaction_id': 12},
                }
            ),
        )

        kwargs = fetch_inputs.fast_path_kwargs()
        self.assertEqual(kwargs['position'], {'owner': 'chain:owner-a'})
        self.assertEqual(kwargs['payload'], {'data': {}})
        self.assertIsInstance(kwargs['position_basis_snapshot'], PositionMetricsPositionBasisSnapshot)
        self.assertIsInstance(kwargs['pool_state_snapshot'], PositionMetricsPoolStateSnapshot)
        self.assertEqual(kwargs['position_basis_snapshot'].raw(), {'basis_transaction_id': 11})
        self.assertEqual(kwargs['pool_state_snapshot'].raw(), {'last_transaction_id': 12})


if __name__ == '__main__':
    unittest.main()
