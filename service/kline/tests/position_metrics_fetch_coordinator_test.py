import sys
import unittest
from inspect import isawaitable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_fetch_coordinator import PositionMetricsFetchCoordinator  # noqa: E402
from query.read_models.position_metrics_fast_path_executor import PositionMetricsFastPathExecutor  # noqa: E402
from query.read_models.position_metrics_fast_path_plan_builder import PositionMetricsFastPathPlanBuilder  # noqa: E402
from query.read_models.position_metrics_fetch_reason_code import PositionMetricsFetchReasonCode  # noqa: E402
from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult  # noqa: E402
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402


class PositionMetricsFetchCoordinatorTest(unittest.TestCase):
    def _run(self, value):
        if isawaitable(value):
            import asyncio
            return asyncio.run(value)
        return value

    def test_fetch_returns_fast_path_without_building_replay_inputs(self):
        class FakeLoader:
            def load_snapshot_inputs(self, **_kwargs):
                return PositionMetricsSnapshotInputs({
                    'position_basis_snapshot': {'basis_transaction_id': 11},
                    'pool_state_snapshot': {'last_transaction_id': 11},
                })

            def load_replay_bundle(self, **_kwargs):
                raise AssertionError('fast path should not build replay inputs')

        class FakeFastPath:
            def resolve(self, **kwargs):
                self.kwargs = dict(kwargs)
                return {'projected_metrics': {'metrics_status': 'exact'}}

        coordinator = PositionMetricsFetchCoordinator(
            payload_builder=lambda **_kwargs: {'data': {}},
            query_input_provider=FakeLoader(),
            fast_path_plan_builder=PositionMetricsFastPathPlanBuilder(
                snapshot_fast_path=FakeFastPath(),
            ),
            fast_path_executor=PositionMetricsFastPathExecutor(),
        )

        payload = self._run(coordinator.fetch(
            position={'owner': 'chain:owner-a', 'pool_application': 'chain:pool-app', 'pool_id': 7},
        ))

        self.assertIsInstance(payload, PositionMetricsFetchedResult)
        self.assertEqual(payload.projected_metrics, {'metrics_status': 'exact'})
        self.assertEqual(payload.fetch_stage, 'snapshot_fast_path')
        self.assertEqual(
            payload.fetch_reason_code,
            PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_HIT,
        )

    def test_fetch_returns_snapshot_unavailable_without_payload_or_replay_fallback(self):
        class FakeLoader:
            def load_snapshot_inputs(self, **_kwargs):
                return PositionMetricsSnapshotInputs({
                    'position_basis_snapshot': None,
                    'pool_state_snapshot': None,
                })

            def load_replay_bundle(self, **_kwargs):
                raise AssertionError('snapshot miss should not build replay inputs')

        def fail_payload_builder(**_kwargs):
            raise AssertionError('snapshot miss should not build projection payload')

        coordinator = PositionMetricsFetchCoordinator(
            payload_builder=fail_payload_builder,
            query_input_provider=FakeLoader(),
            fast_path_plan_builder=PositionMetricsFastPathPlanBuilder(),
            fast_path_executor=PositionMetricsFastPathExecutor(),
        )

        result = self._run(coordinator.fetch(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'current_liquidity': '12',
            },
        ))

        self.assertIsInstance(result, PositionMetricsFetchedResult)
        self.assertEqual(result.fetch_stage, 'snapshot_unavailable')
        self.assertEqual(
            result.fetch_reason_code,
            PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_NO_FALLBACK,
        )
        self.assertEqual(result.projected_metrics['metrics_status'], 'snapshot_unavailable')
        self.assertEqual(result.projected_metrics['position_liquidity'], '12')
        self.assertEqual(result.projected_metrics['computation_blockers'], ['missing_position_metrics_snapshot'])


    def test_fetch_does_not_hide_incomplete_snapshot_payload(self):
        class FakeLoader:
            def load_snapshot_inputs(self, **_kwargs):
                return PositionMetricsSnapshotInputs({
                    'position_basis_snapshot': {'basis_transaction_id': 11},
                    'pool_state_snapshot': {'last_transaction_id': 11},
                })

        def fail_payload_builder(**_kwargs):
            raise RuntimeError('position_metrics_projection_payload_incomplete')

        coordinator = PositionMetricsFetchCoordinator(
            payload_builder=fail_payload_builder,
            query_input_provider=FakeLoader(),
            fast_path_plan_builder=PositionMetricsFastPathPlanBuilder(),
            fast_path_executor=PositionMetricsFastPathExecutor(),
        )

        with self.assertRaisesRegex(RuntimeError, 'position_metrics_projection_payload_incomplete'):
            self._run(coordinator.fetch(
                position={
                    'owner': 'chain:owner-a',
                    'pool_application': 'chain:pool-app',
                    'pool_id': 7,
                    'current_liquidity': '12',
                },
            ))


if __name__ == '__main__':
    unittest.main()
