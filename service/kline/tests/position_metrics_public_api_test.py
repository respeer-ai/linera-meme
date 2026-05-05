import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_public_api import PositionMetricsPublicApi  # noqa: E402


class PositionMetricsPublicApiTest(unittest.IsolatedAsyncioTestCase):
    async def test_public_api_delegates_to_entrypoint_runtime_and_replay_boundaries(self):
        class FakeLivePayloadApi:
            def parse_account(self, account):
                return {'parsed': account}

            def build_position_metrics_query(self, owner):
                return {'query': owner}

            async def fetch_payload(self, *args, **kwargs):
                self.fetch_args = args
                self.fetch_kwargs = dict(kwargs)
                return {'payload': True}

        class FakeEntrypoint:
            def __init__(self):
                self.enrich_calls = []

            def enrich_position_metrics_from_payload(self, *args, **kwargs):
                self.enrich_calls.append({
                    'args': args,
                    'kwargs': dict(kwargs),
                })
                return {'enriched': True}

            def plan_position_metrics_from_payload(self, *args, **kwargs):
                self.plan_args = args
                self.plan_kwargs = dict(kwargs)
                return {'planned': True}

        class FakeReplayEntrypoint:
            def inspect_pool_history_replay(self, history, **kwargs):
                self.history = list(history)
                self.kwargs = dict(kwargs)
                return {'audit': True}

        live_payload_api = FakeLivePayloadApi()
        entrypoint = FakeEntrypoint()
        replay_entrypoint = FakeReplayEntrypoint()
        class FakeFetcherFactory:
            def build(self, *, query_input_provider):
                return {
                    'fetcher': True,
                    'query_input_provider': query_input_provider,
                }

        default_post = object()
        public_api = PositionMetricsPublicApi(
            live_payload_api=live_payload_api,
            entrypoint=entrypoint,
            replay_entrypoint=replay_entrypoint,
            fetcher_factory=FakeFetcherFactory(),
            default_post=default_post,
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

        fetched = await public_api.fetch_live_position_metrics(
            {'pool_application': 'chain:pool-app'},
            'http://swap',
            replay_bundle=object(),
        )
        planned = public_api.plan_position_metrics_from_payload(
            {'pool_application': 'chain:pool-app'},
            {'data': {}},
        )
        enriched = public_api.enrich_position_metrics_from_payload(
            {'pool_application': 'chain:pool-app'},
            {'data': {}},
            replay_bundle='bundle',
        )

        self.assertEqual(fetched, {'enriched': True})
        self.assertEqual(planned, {'planned': True})
        self.assertEqual(enriched, {'enriched': True})
        self.assertEqual(replay_entrypoint.history, [{'transaction_id': 1}])
        self.assertEqual(
            replay_entrypoint.kwargs,
            {
                'virtual_initial_liquidity': True,
                'swap_out_tolerance_attos': 7,
            },
        )
        self.assertEqual(live_payload_api.fetch_args, ({'pool_application': 'chain:pool-app'}, 'http://swap'))
        self.assertIs(live_payload_api.fetch_kwargs['post'], default_post)
        self.assertEqual(
            entrypoint.plan_args,
            ({'pool_application': 'chain:pool-app'}, {'data': {}}),
        )
        self.assertEqual(
            entrypoint.enrich_calls[0]['args'],
            ({'pool_application': 'chain:pool-app'}, {'payload': True}),
        )
        self.assertIsNotNone(entrypoint.enrich_calls[0]['kwargs']['replay_bundle'])
        self.assertEqual(entrypoint.enrich_calls[1]['kwargs']['replay_bundle'], 'bundle')
