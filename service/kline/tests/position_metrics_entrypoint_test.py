import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_entrypoint import PositionMetricsEntrypoint  # noqa: E402


class PositionMetricsEntrypointTest(unittest.IsolatedAsyncioTestCase):
    async def test_delegates_plan_and_enrich_calls(self):
        class FakePayloadResult:
            def __init__(self, metrics):
                self.metrics = metrics

        class FakePayloadPlanner:
            def plan(self, *args):
                self.plan_args = args
                return {'planned': True}

        class FakePayloadEnricher:
            def __init__(self):
                self.calls = []

            def enrich(self, *args, **kwargs):
                self.calls.append({
                    'args': args,
                    'kwargs': dict(kwargs),
                })
                return FakePayloadResult({'enriched': True})

        payload_planner = FakePayloadPlanner()
        payload_enricher = FakePayloadEnricher()
        entrypoint = PositionMetricsEntrypoint(
            payload_planner=payload_planner,
            payload_enricher=payload_enricher,
        )
        planned = entrypoint.plan_position_metrics_from_payload(
            {'pool_application': 'chain:pool-app'},
            {'data': {}},
        )
        enriched_result = entrypoint.enrich_position_metrics_from_payload_result(
            {'pool_application': 'chain:pool-app'},
            {'data': {}},
            replay_bundle='bundle-c',
        )
        enriched = entrypoint.enrich_position_metrics_from_payload(
            {'pool_application': 'chain:pool-app'},
            {'data': {}},
            replay_bundle='bundle-b',
        )

        self.assertEqual(planned, {'planned': True})
        self.assertEqual(enriched_result.metrics, {'enriched': True})
        self.assertEqual(enriched, {'enriched': True})
        self.assertEqual(
            payload_planner.plan_args,
            ({'pool_application': 'chain:pool-app'}, {'data': {}}),
        )
        self.assertEqual(
            payload_enricher.calls[0]['args'],
            ({'pool_application': 'chain:pool-app'}, {'data': {}}),
        )
        self.assertEqual(payload_enricher.calls[0]['kwargs']['replay_bundle'], 'bundle-c')
        self.assertEqual(payload_enricher.calls[1]['kwargs']['replay_bundle'], 'bundle-b')
