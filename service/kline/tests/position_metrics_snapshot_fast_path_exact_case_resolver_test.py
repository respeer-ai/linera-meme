import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from query.read_models.position_metrics_position_basis_snapshot import (  # noqa: E402
    PositionMetricsPositionBasisSnapshot,
)
from query.read_models.position_metrics_snapshot_fast_path_exact_case_resolver import (  # noqa: E402
    PositionMetricsSnapshotFastPathExactCaseResolver,
)


class PositionMetricsSnapshotFastPathExactCaseResolverTest(unittest.TestCase):
    def test_accepts_position_basis_snapshot_objects(self):
        resolver = PositionMetricsSnapshotFastPathExactCaseResolver(
            materialized_exact_current_principal_case=lambda snapshot: (
                'materialized_case'
                if isinstance(snapshot, PositionMetricsPositionBasisSnapshot)
                else None
            )
        )

        exact_case = resolver.resolve(
            position_basis_snapshot=PositionMetricsPositionBasisSnapshot(
                {
                    'basis_type': 'add_liquidity',
                }
            ),
            owner_receives_protocol_fees=False,
            last_transaction_id=11,
            basis_transaction_id=10,
            fee_free_basis_transaction_id=10,
            liquidity_value=Decimal('5'),
            tracked_liquidity_value=Decimal('5'),
        )

        self.assertEqual(exact_case, 'materialized_case')
