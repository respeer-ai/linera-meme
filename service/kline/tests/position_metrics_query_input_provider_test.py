import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_product_state_query_input_provider import PositionMetricsProductStateQueryInputProvider  # noqa: E402
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402
from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError  # noqa: E402


class PositionMetricsProductStateQueryInputProviderTest(unittest.TestCase):
    def test_loads_snapshot_inputs_from_product_state_repository(self):
        class FakeRepository:
            def __init__(self):
                self.calls = []

            def get_snapshot_inputs(self, **kwargs):
                self.calls.append(('get_snapshot_inputs', dict(kwargs)))
                return {
                    'position_basis_snapshot': {'basis_transaction_id': 11},
                    'pool_state_snapshot': {'last_transaction_id': 13},
                }

        repository = FakeRepository()
        provider = PositionMetricsProductStateQueryInputProvider(
            snapshot_inputs_repository=repository,
        )
        position = {
            'owner': 'chain:owner-a',
            'pool_application': 'chain:pool-app',
            'pool_id': 7,
            'status': 'active',
            'opened_at': 1234,
        }

        snapshot_inputs = provider.load_snapshot_inputs(position=position)

        self.assertIsInstance(snapshot_inputs, PositionMetricsSnapshotInputs)
        self.assertEqual(snapshot_inputs.position_basis_snapshot().raw()['basis_transaction_id'], 11)
        self.assertEqual(
            repository.calls,
            [
                ('get_snapshot_inputs', {'owner': 'chain:owner-a', 'pool_application_id': 'chain:pool-app', 'status': 'active'}),
            ],
        )

    def test_requires_snapshot_boundary_contract(self):
        with self.assertRaises(ProjectionQueryUnavailableError) as context:
            PositionMetricsProductStateQueryInputProvider(
                snapshot_inputs_repository=None,
            ).load_snapshot_inputs(
                position={
                    'owner': 'chain:owner-a',
                    'pool_application': 'chain:pool-app',
                    'pool_id': 7,
                    'status': 'active',
                    'opened_at': 1234,
                }
            )

        self.assertEqual(context.exception.query_name, 'position_metrics_snapshot_inputs')


if __name__ == '__main__':
    unittest.main()
