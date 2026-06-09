import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_public_api import PositionMetricsPublicApi  # noqa: E402


class PositionMetricsPublicApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_public_api_delegates_to_current_fetcher_and_replay_audit_boundaries(self):
        class FakeReplayEntrypoint:
            def inspect_pool_history_replay(self, history, **kwargs):
                self.history = list(history)
                self.kwargs = dict(kwargs)
                return {'audit': True}

        class FakeFetcherFactory:
            def build(self, *, query_input_provider):
                return {
                    'fetcher': True,
                    'query_input_provider': query_input_provider,
                }

        replay_entrypoint = FakeReplayEntrypoint()
        public_api = PositionMetricsPublicApi(
            replay_entrypoint=replay_entrypoint,
            fetcher_factory=FakeFetcherFactory(),
            default_swap_out_tolerance_attos=7,
        )

        self.assertEqual(
            public_api.build_fetcher(query_input_provider='provider'),
            {'fetcher': True, 'query_input_provider': 'provider'},
        )
        self.assertEqual(
            public_api.inspect_pool_history_replay(
                [{'transaction_id': 1}],
                virtual_initial_liquidity=True,
            ),
            {'audit': True},
        )
        self.assertEqual(replay_entrypoint.history, [{'transaction_id': 1}])
        self.assertEqual(
            replay_entrypoint.kwargs,
            {
                'virtual_initial_liquidity': True,
                'swap_out_tolerance_attos': 7,
            },
        )


if __name__ == '__main__':
    unittest.main()
