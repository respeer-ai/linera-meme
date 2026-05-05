class PostIngestPipeline:
    def __init__(
        self,
        *,
        normalization_replay_driver,
        market_derivation_replay_driver,
    ):
        self.normalization_replay_driver = normalization_replay_driver
        self.market_derivation_replay_driver = market_derivation_replay_driver

    def run_until_caught_up(
        self,
        *,
        reprocess_reason: str | None = None,
    ) -> dict[str, object]:
        normalization_result = self.normalization_replay_driver.run_all_until_caught_up(
            reprocess_reason=reprocess_reason,
        )
        market_derivation_result = self.market_derivation_replay_driver.run_all_until_caught_up(
            reprocess_reason=reprocess_reason,
        )
        return {
            'reprocess_reason': reprocess_reason,
            'normalization': normalization_result,
            'market_derivation': market_derivation_result,
        }
