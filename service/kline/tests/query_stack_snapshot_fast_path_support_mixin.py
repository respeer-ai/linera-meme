import sys
from pathlib import Path


TEST_ROOT = Path(__file__).resolve().parent
if str(TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(TEST_ROOT))

from query_stack_test_support import QueryStackTestSupport


QueryStackTestSupport.install()


from query.read_models.position_metrics_snapshot_fast_path import PositionMetricsSnapshotFastPath  # noqa: E402
from query.read_models.position_metrics_snapshot_shadow_evaluator import PositionMetricsSnapshotShadowEvaluator  # noqa: E402
from storage.mysql.position_metrics_snapshot_semantic_facts_projector import (  # noqa: E402
    PositionMetricsSnapshotSemanticFactsProjector,
)


class QueryStackSnapshotFastPathSupportMixin:
    def _resolve(self, **kwargs):
        kwargs['position_basis_snapshot'] = self._project_snapshot(
            kwargs.get('position_basis_snapshot')
        )
        return PositionMetricsSnapshotFastPath().resolve(**kwargs)

    def _evaluate(self, **kwargs):
        kwargs['position_basis_snapshot'] = self._project_snapshot(
            kwargs.get('position_basis_snapshot')
        )
        return PositionMetricsSnapshotShadowEvaluator().evaluate(**kwargs)

    def _project_snapshot(self, snapshot):
        return PositionMetricsSnapshotSemanticFactsProjector().project(snapshot)
