import sys
import unittest
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport
from query_stack_snapshot_fast_path_baseline_mixin import QueryStackSnapshotFastPathBaselineMixin
from query_stack_snapshot_fast_path_fee_to_mixin import QueryStackSnapshotFastPathFeeToMixin
from query_stack_snapshot_fast_path_materialized_mixin import QueryStackSnapshotFastPathMaterializedMixin
from query_stack_snapshot_fast_path_support_mixin import QueryStackSnapshotFastPathSupportMixin
from query_stack_snapshot_shadow_mixin import QueryStackSnapshotShadowMixin


QueryStackTestSupport.install()


class QueryStackSnapshotFastPathTest(
    QueryStackSnapshotFastPathSupportMixin,
    QueryStackSnapshotFastPathBaselineMixin,
    QueryStackSnapshotFastPathMaterializedMixin,
    QueryStackSnapshotFastPathFeeToMixin,
    QueryStackSnapshotShadowMixin,
    unittest.TestCase,
):
    pass


if __name__ == '__main__':
    unittest.main()
