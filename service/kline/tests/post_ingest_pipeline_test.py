import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = ROOT / 'src'

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


from ingestion.post_ingest_pipeline import PostIngestPipeline  # noqa: E402


class PostIngestPipelineTest(unittest.TestCase):
    class FakeReplayDriver:
        def __init__(self, result):
            self.result = result
            self.calls = []

        def run_all_until_caught_up(self, *, reprocess_reason=None):
            self.calls.append(reprocess_reason)
            return self.result

    def test_runs_normalization_then_market_derivation_until_caught_up(self):
        normalization_driver = self.FakeReplayDriver({
            'processed_count': 2,
            'caught_up': True,
        })
        market_derivation_driver = self.FakeReplayDriver({
            'processed_count': 1,
            'caught_up': True,
        })
        pipeline = PostIngestPipeline(
            normalization_replay_driver=normalization_driver,
            market_derivation_replay_driver=market_derivation_driver,
        )

        result = pipeline.run_until_caught_up(
            reprocess_reason='catch_up:chain-a',
        )

        self.assertEqual(normalization_driver.calls, ['catch_up:chain-a'])
        self.assertEqual(market_derivation_driver.calls, ['catch_up:chain-a'])
        self.assertEqual(
            result,
            {
                'reprocess_reason': 'catch_up:chain-a',
                'normalization': {'processed_count': 2, 'caught_up': True},
                'market_derivation': {'processed_count': 1, 'caught_up': True},
            },
        )


if __name__ == '__main__':
    unittest.main()
