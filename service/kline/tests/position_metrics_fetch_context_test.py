import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_fetch_context import PositionMetricsFetchContext  # noqa: E402
from query.read_models.position_metrics_pool_state_snapshot import PositionMetricsPoolStateSnapshot  # noqa: E402
from query.read_models.position_metrics_position_basis_snapshot import PositionMetricsPositionBasisSnapshot  # noqa: E402
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402


class PositionMetricsFetchContextTest(unittest.TestCase):
    def test_builds_fast_path_kwargs_from_snapshot_inputs(self):
        class FakeLoader:
            def __init__(self):
                self.calls = []

            def load_snapshot_inputs(self, **kwargs):
                self.calls.append(('load_snapshot_inputs', dict(kwargs)))
                return PositionMetricsSnapshotInputs(
                    {
                        'position_basis_snapshot': {'basis_transaction_id': 11},
                        'pool_state_snapshot': {'last_transaction_id': 12},
                    }
                )

        position = {'owner': 'chain:owner-a', 'pool_application': 'chain:pool-app', 'pool_id': 7}
        payload = {'data': {}}
        loader = FakeLoader()
        context = PositionMetricsFetchContext(
            position=position,
            payload=payload,
            query_input_provider=loader,
        )

        fetch_inputs = context.fetch_inputs()
        kwargs = fetch_inputs.fast_path_kwargs()
        snapshot_inputs = fetch_inputs.snapshot_inputs()

        self.assertEqual(kwargs['position'], position)
        self.assertEqual(kwargs['payload'], payload)
        self.assertIsInstance(kwargs['position_basis_snapshot'], PositionMetricsPositionBasisSnapshot)
        self.assertIsInstance(kwargs['pool_state_snapshot'], PositionMetricsPoolStateSnapshot)
        self.assertEqual(kwargs['position_basis_snapshot'].raw(), {'basis_transaction_id': 11})
        self.assertEqual(kwargs['pool_state_snapshot'].raw(), {'last_transaction_id': 12})
        self.assertEqual(snapshot_inputs.position_basis_snapshot().raw(), {'basis_transaction_id': 11})
        self.assertEqual(snapshot_inputs.pool_state_snapshot().raw(), {'last_transaction_id': 12})
        self.assertEqual(
            loader.calls,
            [('load_snapshot_inputs', {'position': position})],
        )


if __name__ == '__main__':
    unittest.main()
