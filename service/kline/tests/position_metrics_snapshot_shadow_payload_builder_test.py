import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_snapshot_shadow_payload_builder import (  # noqa: E402
    PositionMetricsSnapshotShadowPayloadBuilder,
)


class PositionMetricsSnapshotShadowPayloadBuilderTest(unittest.TestCase):
    def test_builds_snapshot_shadow_envelope(self):
        payload = PositionMetricsSnapshotShadowPayloadBuilder().build(
            position={
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'status': 'active',
            },
            projected_metrics={
                'metrics_status': 'exact_no_swap_history',
            },
            fee_calculation_complete=True,
            principal_calculation_complete=False,
            snapshot_shadow={
                'comparable': True,
            },
        )

        self.assertEqual(
            payload,
            {
                'owner': 'chain:owner-a',
                'pool_application': 'chain:pool-app',
                'pool_id': 7,
                'status': 'active',
                'metrics_status': 'exact_no_swap_history',
                'fee_calculation_complete': True,
                'principal_calculation_complete': False,
                'snapshot_shadow': {
                    'comparable': True,
                },
            },
        )
