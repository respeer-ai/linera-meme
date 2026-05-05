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
from query.read_models.position_metrics_fetch_plan import PositionMetricsFetchPlan  # noqa: E402
from query.read_models.position_metrics_payload_only_executor import PositionMetricsPayloadOnlyExecutor  # noqa: E402
from query.read_models.position_metrics_fetch_reason_code import PositionMetricsFetchReasonCode  # noqa: E402
from query.read_models.position_metrics_replay_fallback_result_builder import PositionMetricsReplayFallbackResultBuilder  # noqa: E402
from query.read_models.position_metrics_replay_fallback_executor import PositionMetricsReplayFallbackExecutor  # noqa: E402
from query.read_models.position_metrics_replay_snapshot_shadow_builder import PositionMetricsReplaySnapshotShadowBuilder  # noqa: E402
from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult  # noqa: E402
from query.read_models.position_metrics_replay_bundle import PositionMetricsReplayBundle  # noqa: E402
from query.read_models.position_metrics_snapshot_inputs import PositionMetricsSnapshotInputs  # noqa: E402
from position_metrics_payload_result import PositionMetricsPayloadResult  # noqa: E402
from position_metrics_payload_decision import PositionMetricsPayloadDecision  # noqa: E402


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
                return {'live_metrics': {'metrics_status': 'exact'}}

        coordinator = PositionMetricsFetchCoordinator(
            payload_builder=lambda **_kwargs: {'data': {}},
            query_input_provider=FakeLoader(),
            fast_path_plan_builder=PositionMetricsFastPathPlanBuilder(
                snapshot_fast_path=FakeFastPath(),
            ),
            plan_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError('fast path should bypass replay enrichment')
            ),
            fast_path_executor=PositionMetricsFastPathExecutor(),
            payload_only_executor=PositionMetricsPayloadOnlyExecutor(),
            replay_fallback_executor=PositionMetricsReplayFallbackExecutor(
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('fast path should bypass replay enrichment')
                ),
                replay_snapshot_shadow_builder=PositionMetricsReplaySnapshotShadowBuilder(),
                replay_fallback_result_builder=PositionMetricsReplayFallbackResultBuilder(),
            ),
        )

        payload = self._run(coordinator.fetch(
            position={'owner': 'chain:owner-a', 'pool_application': 'chain:pool-app', 'pool_id': 7},
        ))

        self.assertIsInstance(payload, PositionMetricsFetchedResult)
        self.assertEqual(payload.live_metrics, {'metrics_status': 'exact'})
        self.assertEqual(payload.fetch_stage, 'snapshot_fast_path')
        self.assertEqual(
            payload.fetch_reason_code,
            PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_HIT,
        )

    def test_fetch_returns_payload_only_metrics_without_shadow_assembly(self):
        class FakeLoader:
            def load_snapshot_inputs(self, **_kwargs):
                return PositionMetricsSnapshotInputs({
                    'position_basis_snapshot': {'basis_transaction_id': 11},
                    'pool_state_snapshot': {'last_transaction_id': 12},
                })

            def load_replay_bundle(self, **_kwargs):
                return None

        coordinator = PositionMetricsFetchCoordinator(
            payload_builder=lambda **_kwargs: {'data': {}},
            query_input_provider=FakeLoader(),
            fast_path_plan_builder=PositionMetricsFastPathPlanBuilder(),
            plan_payload=lambda *_args, **_kwargs: PositionMetricsPayloadResult(
                metrics={'metrics_status': 'partial_live_redeemable_only'},
                decision=PositionMetricsPayloadDecision.PAYLOAD_ONLY,
                reason_code='payload_history_unavailable',
            ),
            fast_path_executor=PositionMetricsFastPathExecutor(),
            payload_only_executor=PositionMetricsPayloadOnlyExecutor(),
            replay_fallback_executor=PositionMetricsReplayFallbackExecutor(
                enrich_payload=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                    AssertionError('payload-only path should bypass replay enrichment')
                ),
                replay_snapshot_shadow_builder=PositionMetricsReplaySnapshotShadowBuilder(),
                replay_fallback_result_builder=PositionMetricsReplayFallbackResultBuilder(),
            ),
        )

        result = self._run(coordinator.fetch(
            position={'owner': 'chain:owner-a', 'pool_application': 'chain:pool-app', 'pool_id': 7},
        ))

        self.assertIsInstance(result, PositionMetricsFetchedResult)
        self.assertEqual(result.live_metrics, {'metrics_status': 'partial_live_redeemable_only'})
        self.assertEqual(result.fetch_stage, 'payload_only')
        self.assertEqual(
            result.fetch_reason_code,
            PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_PAYLOAD_ONLY,
        )

    def test_fetch_builds_live_metrics_and_shadow_from_replay_inputs(self):
        class FakeLoader:
            def load_snapshot_inputs(self, **_kwargs):
                return PositionMetricsSnapshotInputs({
                    'position_basis_snapshot': {'basis_transaction_id': 11},
                    'pool_state_snapshot': {'last_transaction_id': 12},
                })

            def load_replay_bundle(self, **_kwargs):
                return PositionMetricsReplayBundle(
                    {
                        'liquidity_history': [{'transaction_id': 11}],
                        'pool_transaction_history': [{'transaction_id': 12}],
                        'pool_swap_count_since_open': 3,
                        'pool_history_gap_summary': {'has_internal_gaps': False},
                        'replay_summary': {
                            'latest_position_transaction_id': 11,
                            'latest_position_created_at': None,
                            'latest_pool_transaction_id': 12,
                            'latest_pool_trade_time_ms': None,
                            'latest_pool_liquidity_event_time_ms': None,
                        },
                    }
                )

        class FakeReplaySnapshotShadowBuilder:
            def build(self, **kwargs):
                self.kwargs = dict(kwargs)
                return {'snapshot_shadow': {'ready': True}}

        captured = {}

        def fake_enrich(position, payload, **kwargs):
            captured['position'] = dict(position)
            captured['payload'] = dict(payload)
            captured.update(kwargs)
            return PositionMetricsPayloadResult(
                metrics={'metrics_status': 'ok'},
                decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                reason_code='payload_requires_history',
            )

        replay_snapshot_shadow_builder = FakeReplaySnapshotShadowBuilder()
        coordinator = PositionMetricsFetchCoordinator(
            payload_builder=lambda **_kwargs: {'data': {}},
            query_input_provider=FakeLoader(),
            fast_path_plan_builder=PositionMetricsFastPathPlanBuilder(),
            plan_payload=lambda *_args, **_kwargs: PositionMetricsPayloadResult(
                metrics={'metrics_status': 'partial_live_redeemable_only'},
                decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                reason_code='payload_requires_history',
            ),
            fast_path_executor=PositionMetricsFastPathExecutor(),
            payload_only_executor=PositionMetricsPayloadOnlyExecutor(),
            replay_fallback_executor=PositionMetricsReplayFallbackExecutor(
                enrich_payload=fake_enrich,
                replay_snapshot_shadow_builder=replay_snapshot_shadow_builder,
                replay_fallback_result_builder=PositionMetricsReplayFallbackResultBuilder(),
            ),
        )

        result = self._run(coordinator.fetch(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
            },
        ))

        self.assertIsInstance(result, PositionMetricsFetchedResult)
        self.assertEqual(result.live_metrics, {'metrics_status': 'ok'})
        self.assertEqual(result.fetch_stage, 'replay_fallback')
        self.assertEqual(
            result.fetch_reason_code,
            PositionMetricsFetchReasonCode.SNAPSHOT_FAST_PATH_MISS_PAYLOAD_REQUIRES_HISTORY,
        )
        self.assertEqual(result.snapshot_shadow, {'snapshot_shadow': {'ready': True}})
        self.assertEqual(captured['replay_bundle'].liquidity_history(), [{'transaction_id': 11}])
        self.assertEqual(captured['replay_bundle'].pool_transaction_history(), [{'transaction_id': 12}])
        self.assertEqual(captured['replay_bundle'].pool_swap_count_since_open(), 3)
        self.assertEqual(captured['replay_bundle'].pool_history_gap_summary(), {'has_internal_gaps': False})
        self.assertEqual(
            replay_snapshot_shadow_builder.kwargs['snapshot_inputs'].position_basis_snapshot().raw(),
            {'basis_transaction_id': 11},
        )
        self.assertEqual(
            replay_snapshot_shadow_builder.kwargs['snapshot_inputs'].pool_state_snapshot().raw(),
            {'last_transaction_id': 12},
        )
        self.assertEqual(
            replay_snapshot_shadow_builder.kwargs['replay_summary'].as_dict(),
            {
                'latest_position_transaction_id': 11,
                'latest_position_created_at': None,
                'latest_pool_transaction_id': 12,
                'latest_pool_trade_time_ms': None,
                'latest_pool_liquidity_event_time_ms': None,
            },
        )
