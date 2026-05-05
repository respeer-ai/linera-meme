import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_fetch_plan import PositionMetricsFetchPlan  # noqa: E402
from query.read_models.position_metrics_fetched_result import PositionMetricsFetchedResult  # noqa: E402
from query.read_models.position_metrics_replay_fallback_executor import PositionMetricsReplayFallbackExecutor  # noqa: E402
from position_metrics_payload_decision import PositionMetricsPayloadDecision  # noqa: E402
from position_metrics_payload_result import PositionMetricsPayloadResult  # noqa: E402


class PositionMetricsReplayFallbackExecutorTest(unittest.TestCase):
    def test_assembles_replay_payload_and_applies_plan_metadata(self):
        class FakeAssembler:
            def assemble(self, **kwargs):
                self.kwargs = dict(kwargs)
                return PositionMetricsFetchedResult(
                    live_metrics=kwargs['live_metrics'],
                    fetch_stage='replay_fallback',
                    fetch_reason_code='snapshot_fast_path_miss_payload_requires_history',
                    snapshot_shadow={'snapshot_shadow': {'readiness': 'candidate'}},
                )

        class FakeFetchContext:
            position = {'pool_id': 7}
            payload = {'data': {}}

            class FakeFetchInputs:
                def snapshot_inputs(self):
                    return 'snapshot-inputs'

                def enrich_kwargs(self):
                    return {'replay_bundle': 'bundle'}

                def replay_summary(self):
                    return 'replay-summary'

            def fetch_inputs(self):
                return self.FakeFetchInputs()

        executor = PositionMetricsReplayFallbackExecutor(
            enrich_payload=lambda *_args, **_kwargs: PositionMetricsPayloadResult(
                metrics={'metrics_status': 'exact'},
                decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                reason_code='payload_requires_history',
            ),
            result_assembler=FakeAssembler(),
        )
        plan = PositionMetricsFetchPlan.replay_fallback(
            PositionMetricsPayloadResult(
                metrics={'metrics_status': 'exact'},
                decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                reason_code='payload_requires_history',
            )
        )

        result = executor.execute(
            plan=plan,
            fetch_context=FakeFetchContext(),
        )
        self.assertIsInstance(result, PositionMetricsFetchedResult)
        self.assertEqual(result.live_metrics, {'metrics_status': 'exact'})
        self.assertEqual(result.snapshot_shadow, {'snapshot_shadow': {'readiness': 'candidate'}})
        self.assertEqual(result.fetch_stage, 'replay_fallback')
        self.assertEqual(result.fetch_reason_code, 'snapshot_fast_path_miss_payload_requires_history')


if __name__ == '__main__':
    unittest.main()
