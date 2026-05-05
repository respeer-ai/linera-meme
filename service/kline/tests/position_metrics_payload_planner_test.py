import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_payload_decision import PositionMetricsPayloadDecision  # noqa: E402
from position_metrics_payload_decision_result import PositionMetricsPayloadDecisionResult  # noqa: E402
from position_metrics_payload_planner import PositionMetricsPayloadPlanner  # noqa: E402


class PositionMetricsPayloadPlannerTest(unittest.TestCase):
    def test_returns_payload_only_result_with_warnings_applied(self):
        planner = PositionMetricsPayloadPlanner(
            payload_semantic_builder=type(
                'FakeBuilder',
                (),
                {'build': lambda self, **_kwargs: {'metrics_status': 'partial_live_redeemable_only'}},
            )(),
            payload_decision_resolver=type(
                'FakeResolver',
                (),
                {
                    'resolve': lambda self, metrics, **_kwargs: PositionMetricsPayloadDecisionResult(
                        decision=PositionMetricsPayloadDecision.PAYLOAD_ONLY,
                        reason_code='payload_history_unavailable',
                        metrics=metrics,
                    )
                },
            )(),
            apply_data_quality_warnings=lambda metrics, **kwargs: {
                **metrics,
                'warnings': kwargs['pool_history_gap_summary'],
            },
            build_transaction_gap_summary=lambda *_args, **_kwargs: {'has_internal_gaps': False},
        )

        result = planner.plan(
            {'owner': 'chain:owner-a'},
            {'data': {}},
            pool_history_gap_summary={'has_internal_gaps': True},
        )

        self.assertEqual(result.decision, PositionMetricsPayloadDecision.PAYLOAD_ONLY)
        self.assertEqual(result.reason_code, 'payload_history_unavailable')
        self.assertEqual(result.metrics['warnings'], {'has_internal_gaps': True})

    def test_returns_history_decision_without_running_history_enrichment(self):
        planner = PositionMetricsPayloadPlanner(
            payload_semantic_builder=type(
                'FakeBuilder',
                (),
                {'build': lambda self, **_kwargs: {'metrics_status': 'partial_live_redeemable_only'}},
            )(),
            payload_decision_resolver=type(
                'FakeResolver',
                (),
                {
                    'resolve': lambda self, metrics, **_kwargs: PositionMetricsPayloadDecisionResult(
                        decision=PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT,
                        reason_code='payload_requires_history',
                        metrics=metrics,
                    )
                },
            )(),
            apply_data_quality_warnings=lambda metrics, **_kwargs: (_ for _ in ()).throw(
                AssertionError('history path should not apply payload-only warnings at planning time')
            ),
            build_transaction_gap_summary=lambda *_args, **_kwargs: {'has_internal_gaps': False},
        )

        result = planner.plan(
            {'owner': 'chain:owner-a'},
            {'data': {}},
            liquidity_history=[],
            pool_transaction_history=[],
            pool_swap_count_since_open=0,
        )

        self.assertEqual(result.decision, PositionMetricsPayloadDecision.NEEDS_HISTORY_ENRICHMENT)
        self.assertEqual(result.reason_code, 'payload_requires_history')


if __name__ == '__main__':
    unittest.main()
