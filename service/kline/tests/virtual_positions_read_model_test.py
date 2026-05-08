import asyncio
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.virtual_positions import VirtualPositionsReadModel  # noqa: E402


class VirtualPositionsReadModelTest(unittest.TestCase):
    def test_enrich_positions_adds_virtual_initial_liquidity_position_from_live_payload(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                self.owner = owner
                return [{
                    'pool_application': 'chain-a:0xpool-app',
                    'pool_id': 7,
                    'token_0': 'AAA',
                    'token_1': 'BBB',
                    'owner': owner,
                    'opened_at': 1000,
                    'updated_at': 1000,
                    'add_tx_count': 1,
                }]

        class FakeLivePayloadApi:
            async def fetch_payload(self, position, swap_base_url, *, post):
                self.calls = (position, swap_base_url, post)
                return {
                    'data': {
                        'virtualInitialLiquidity': True,
                        'liquidity': {
                            'liquidity': '5',
                            'amount0': '40',
                            'amount1': '80',
                        },
                    }
                }

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            live_payload_api=FakeLivePayloadApi(),
            swap_base_url='http://swap-host/api/swap/query',
            post=object(),
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-a:owner-a',
            status='active',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertTrue(result[0]['is_virtual_position'])
        self.assertEqual(result[0]['current_liquidity'], '5')
        self.assertEqual(result[0]['added_liquidity'], '5')
        self.assertEqual(result[0]['removed_liquidity'], '0')

    def test_enrich_positions_falls_back_to_pool_catalog_when_projection_has_no_candidates(self):
        class FakeProjectionRepository:
            def get_owner_candidate_histories(self, *, owner):
                self.owner = owner
                return []

        class FakeLivePayloadApi:
            async def fetch_payload(self, position, swap_base_url, *, post):
                self.calls = (position, swap_base_url, post)
                return {
                    'data': {
                        'virtualInitialLiquidity': True,
                        'liquidity': {
                            'liquidity': '7',
                            'amount0': '70',
                            'amount1': '90',
                        },
                    }
                }

        async def fake_pool_catalog_loader():
            return [{
                'poolId': 9,
                'token0': 'DOGE',
                'token1': None,
                'poolApplication': {
                    'chain_id': 'chain-b',
                    'owner': '0xpool-app',
                },
            }]

        read_model = VirtualPositionsReadModel(
            projection_repository=FakeProjectionRepository(),
            live_payload_api=FakeLivePayloadApi(),
            swap_base_url='http://swap-host/api/swap/query',
            post=object(),
            pool_catalog_loader=fake_pool_catalog_loader,
        )

        result = asyncio.run(read_model.enrich_positions(
            owner='chain-b:owner-b',
            status='active',
            positions=[],
        ))

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['pool_application'], 'chain-b:0xpool-app')
        self.assertEqual(result[0]['token_1'], 'TLINERA')
        self.assertEqual(result[0]['position_kind'], 'virtual_initial_liquidity')
        self.assertTrue(result[0]['is_virtual_position'])
        self.assertEqual(result[0]['current_liquidity'], '7')


if __name__ == '__main__':
    unittest.main()
