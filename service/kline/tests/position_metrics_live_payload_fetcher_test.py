import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from position_metrics_live_payload_fetcher import PositionMetricsLivePayloadFetcher  # noqa: E402


class PositionMetricsLivePayloadFetcherTest(unittest.IsolatedAsyncioTestCase):
    async def test_fetch_uses_supplied_client_and_parsed_owner(self):
        class FakeClient:
            async def get_position_metrics_payload(self, *, owner):
                self.owner = owner
                return {'payload': True}

        client = FakeClient()
        fetcher = PositionMetricsLivePayloadFetcher(
            parse_account=lambda account: {'chain_id': 'chain-a', 'owner': account.split(':', 1)[1]},
        )

        payload = await fetcher.fetch(
            client=client,
            owner_account='chain-a:0xowner-a',
        )

        self.assertEqual(payload, {'payload': True})
        self.assertEqual(
            client.owner,
            {'chain_id': 'chain-a', 'owner': '0xowner-a'},
        )
