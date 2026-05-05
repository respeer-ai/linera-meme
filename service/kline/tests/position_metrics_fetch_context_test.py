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
from query.read_models.position_metrics_replay_bundle import PositionMetricsReplayBundle  # noqa: E402
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

            def load_replay_bundle(self, **_kwargs):
                raise AssertionError('fast path should not build replay inputs')

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

    def test_builds_enrich_kwargs_and_shadow_summary_from_replay_inputs(self):
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

            def load_replay_bundle(self, **kwargs):
                self.calls.append(('load_replay_bundle', dict(kwargs)))

                class ReplayBundle:
                    def liquidity_history(self):
                        return [{'transaction_id': 11}]

                    def pool_transaction_history(self):
                        return [{'transaction_id': 12}]

                    def pool_swap_count_since_open(self):
                        return 3

                    def pool_history_gap_summary(self):
                        return {'has_internal_gaps': False}

                    def replay_summary(self):
                        return {
                            'latest_position_transaction_id': 11,
                            'latest_position_created_at': None,
                            'latest_pool_transaction_id': 12,
                            'latest_pool_trade_time_ms': None,
                            'latest_pool_liquidity_event_time_ms': None,
                        }

                return PositionMetricsReplayBundle(
                    {
                        'liquidity_history': ReplayBundle().liquidity_history(),
                        'pool_transaction_history': ReplayBundle().pool_transaction_history(),
                        'pool_swap_count_since_open': ReplayBundle().pool_swap_count_since_open(),
                        'pool_history_gap_summary': ReplayBundle().pool_history_gap_summary(),
                        'replay_summary': ReplayBundle().replay_summary(),
                    }
                )

        position = {'owner': 'chain:owner-a', 'pool_application': 'chain:pool-app', 'pool_id': 7}
        context = PositionMetricsFetchContext(
            position=position,
            payload={'data': {}},
            query_input_provider=FakeLoader(),
        )

        fetch_inputs = context.fetch_inputs()
        enrich_kwargs = fetch_inputs.enrich_kwargs()
        replay_summary = fetch_inputs.replay_summary()

        self.assertEqual(enrich_kwargs['replay_bundle'].liquidity_history(), [{'transaction_id': 11}])
        self.assertEqual(enrich_kwargs['replay_bundle'].pool_transaction_history(), [{'transaction_id': 12}])
        self.assertEqual(enrich_kwargs['replay_bundle'].pool_swap_count_since_open(), 3)
        self.assertEqual(enrich_kwargs['replay_bundle'].pool_history_gap_summary(), {'has_internal_gaps': False})
        self.assertIsInstance(enrich_kwargs['position_basis_snapshot'], PositionMetricsPositionBasisSnapshot)
        self.assertIsInstance(enrich_kwargs['pool_state_snapshot'], PositionMetricsPoolStateSnapshot)
        self.assertEqual(enrich_kwargs['position_basis_snapshot'].raw(), {'basis_transaction_id': 11})
        self.assertEqual(enrich_kwargs['pool_state_snapshot'].raw(), {'last_transaction_id': 12})
        self.assertEqual(
            replay_summary.as_dict(),
            {
                'latest_position_transaction_id': 11,
                'latest_position_created_at': None,
                'latest_pool_transaction_id': 12,
                'latest_pool_trade_time_ms': None,
                'latest_pool_liquidity_event_time_ms': None,
            },
        )
        self.assertEqual(
            context.query_input_provider.calls,
            [
                ('load_snapshot_inputs', {'position': position}),
                ('load_replay_bundle', {'position': position}),
            ],
        )
