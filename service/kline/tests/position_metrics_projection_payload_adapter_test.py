import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_projection_payload_adapter import (  # noqa: E402
    PositionMetricsProjectionPayloadAdapter,
)


class FakeSnapshotInputs:
    def __init__(self, *, position_basis_snapshot, pool_state_snapshot):
        self._position_basis_snapshot = position_basis_snapshot
        self._pool_state_snapshot = pool_state_snapshot

    def position_basis_snapshot(self):
        return self._position_basis_snapshot

    def pool_state_snapshot(self):
        return self._pool_state_snapshot


class PositionMetricsProjectionPayloadAdapterTest(unittest.TestCase):
    def test_recorded_position_uses_position_current_liquidity_not_owner_liquidity_snapshot(self):
        payload = PositionMetricsProjectionPayloadAdapter().build_payload(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'status': 'active',
                'current_liquidity': '6.42',
            },
            snapshot_inputs=FakeSnapshotInputs(
                position_basis_snapshot={
                    'current_liquidity': '8',
                    'semantic_facts': {
                        'fee_to_continuity': {
                            'fee_to_account_latest_known': (
                                '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a'
                            ),
                        },
                    },
                },
                pool_state_snapshot={
                    'current_total_supply': '100',
                    'current_reserve_0': '200',
                    'current_reserve_1': '300',
                    'state_payload_json': {},
                },
            ),
        )

        self.assertEqual(payload['data']['liquidity']['liquidity'], '6.42')
        self.assertEqual(payload['data']['liquidity']['amount0'], '12.84')
        self.assertEqual(payload['data']['liquidity']['amount1'], '19.26')

    def test_virtual_position_can_use_snapshot_liquidity(self):
        payload = PositionMetricsProjectionPayloadAdapter().build_payload(
            position={
                'owner': '0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa@chain-a',
                'status': 'virtual',
                'position_kind': 'virtual_initial_liquidity',
                'is_virtual_position': True,
                'current_liquidity': '0',
            },
            snapshot_inputs=FakeSnapshotInputs(
                position_basis_snapshot={
                    'current_liquidity': '8',
                    'semantic_facts': {},
                },
                pool_state_snapshot={
                    'current_total_supply': '100',
                    'current_reserve_0': '200',
                    'current_reserve_1': '300',
                    'state_payload_json': {},
                },
            ),
        )

        self.assertEqual(payload['data']['liquidity']['liquidity'], '8')


if __name__ == '__main__':
    unittest.main()
