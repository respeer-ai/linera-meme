import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_product_state_query_input_provider import PositionMetricsProductStateQueryInputProvider  # noqa: E402
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402
from query.read_models.position_metrics_replay_bundle import PositionMetricsReplayBundle  # noqa: E402
from query.read_models.position_metrics_replay_facts import PositionMetricsReplayFacts  # noqa: E402
from storage.mysql.projection_query_unavailable_error import ProjectionQueryUnavailableError  # noqa: E402


class PositionMetricsProductStateQueryInputProviderTest(unittest.TestCase):
    def test_loads_snapshot_inputs_and_replay_bundle_from_product_state_repositories(self):
        class FakeRepository:
            def __init__(self):
                self.calls = []

            def get_snapshot_inputs(self, **kwargs):
                self.calls.append(('get_snapshot_inputs', dict(kwargs)))
                return {
                    'position_basis_snapshot': {'basis_transaction_id': 11},
                    'pool_state_snapshot': {'last_transaction_id': 13},
                }

            def get_replay_facts(self, **kwargs):
                self.calls.append(('get_replay_facts', dict(kwargs)))
                return {
                    'liquidity_history': [{'transaction_id': 11}],
                    'pool_transaction_history': [{'transaction_id': 12}],
                    'pool_swap_count_since_open': 1,
                    'pool_history_gap_summary': {'has_internal_gaps': False},
                    'replay_summary': {'latest_pool_transaction_id': 12},
                }

        repository = FakeRepository()
        provider = PositionMetricsProductStateQueryInputProvider(
            snapshot_inputs_repository=repository,
            replay_facts_repository=repository,
        )
        position = {
            'owner': 'chain:owner-a',
            'pool_application': 'chain:pool-app',
            'pool_id': 7,
            'status': 'active',
            'opened_at': 1234,
        }

        snapshot_inputs = provider.load_snapshot_inputs(position=position)
        replay_bundle = provider.load_replay_bundle(position=position)

        self.assertIsInstance(snapshot_inputs, PositionMetricsSnapshotInputs)
        self.assertEqual(snapshot_inputs.position_basis_snapshot().raw()['basis_transaction_id'], 11)
        self.assertIsInstance(replay_bundle, PositionMetricsReplayBundle)
        self.assertEqual(replay_bundle.pool_swap_count_since_open(), 1)
        self.assertEqual(
            repository.calls,
            [
                ('get_snapshot_inputs', {'owner': 'chain:owner-a', 'pool_application_id': 'chain:pool-app', 'status': 'active'}),
                ('get_replay_facts', {'owner': 'chain:owner-a', 'pool_application': 'chain:pool-app', 'pool_id': 7, 'opened_at': 1234}),
            ],
        )

    def test_wraps_replay_fact_objects(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return None

            def get_replay_facts(self, **_kwargs):
                return PositionMetricsReplayFacts(
                    {
                        'liquidity_history': [{'transaction_id': 11}],
                        'pool_transaction_history': [{'transaction_id': 12}],
                        'pool_swap_count_since_open': 1,
                        'pool_history_gap_summary': {'has_internal_gaps': False},
                        'replay_summary': {'latest_pool_transaction_id': 12},
                    }
                )

        replay_bundle = PositionMetricsProductStateQueryInputProvider(
            snapshot_inputs_repository=FakeRepository(),
            replay_facts_repository=FakeRepository(),
        ).load_replay_bundle(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'status': 'active',
                'opened_at': 1234,
            }
        )

        self.assertIsInstance(replay_bundle, PositionMetricsReplayBundle)
        self.assertEqual(replay_bundle.pool_transaction_history(), [{'transaction_id': 12}])

    def test_requires_snapshot_boundary_contract(self):
        class FakeRepository:
            pass

        with self.assertRaises(ProjectionQueryUnavailableError) as context:
            PositionMetricsProductStateQueryInputProvider(
                snapshot_inputs_repository=None,
                replay_facts_repository=FakeRepository(),
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

    def test_requires_replay_boundary_contract(self):
        class FakeRepository:
            def get_snapshot_inputs(self, **_kwargs):
                return None

        with self.assertRaises(ProjectionQueryUnavailableError) as context:
            PositionMetricsProductStateQueryInputProvider(
                snapshot_inputs_repository=FakeRepository(),
                replay_facts_repository=None,
            ).load_replay_bundle(
                position={
                    'owner': 'chain:owner-a',
                    'pool_application': 'chain:pool-app',
                    'pool_id': 7,
                    'status': 'active',
                    'opened_at': 1234,
                }
            )

        self.assertEqual(context.exception.query_name, 'position_metrics_replay_facts')
