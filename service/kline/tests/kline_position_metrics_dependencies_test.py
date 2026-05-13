import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from kline_position_metrics_dependencies import KlinePositionMetricsDependencies  # noqa: E402


class KlinePositionMetricsDependenciesTest(unittest.TestCase):
    class FakeOverrides(dict):
        pass

    class FakeRuntime:
        def __init__(self):
            self.calls = []
            self.positions_repo = object()
            self.snapshot_repo = object()
            self.replay_facts_repo = object()
            self.pool_history_repo = object()

        def position_metrics_positions_projection_repository(self):
            self.calls.append('positions')
            return self.positions_repo

        def position_metrics_snapshot_inputs_projection_repository(self):
            self.calls.append('snapshot')
            return self.snapshot_repo

        def position_metrics_replay_facts_projection_repository(self):
            self.calls.append('replay')
            return self.replay_facts_repo

        def settled_pool_history_projection_repository(self):
            self.calls.append('pool_history')
            return self.pool_history_repo

    def test_resolve_uses_explicit_runtime_repository_accessors(self):
        runtime = self.FakeRuntime()

        dependencies = KlinePositionMetricsDependencies.resolve(
            runtime=runtime,
            overrides=self.FakeOverrides(),
        )

        self.assertIs(dependencies.positions_repository(), runtime.positions_repo)
        self.assertIs(dependencies.snapshot_inputs_repository(), runtime.snapshot_repo)
        self.assertIs(dependencies.replay_facts_repository(), runtime.replay_facts_repo)
        self.assertIs(dependencies.pool_history_repository(), runtime.pool_history_repo)
        self.assertEqual(runtime.calls, ['positions', 'snapshot', 'replay', 'pool_history'])


if __name__ == '__main__':
    unittest.main()
