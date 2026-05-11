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

    def run_bounded(
        self,
        *,
        reprocess_reason: str | None = None,
        max_batches_per_table: int = 1,
    ) -> dict[str, object]:
        normalization_result = self.normalization_replay_driver.run_all(
            reprocess_reason=reprocess_reason,
            max_batches_per_table=max_batches_per_table,
        )
        market_derivation_result = self.market_derivation_replay_driver.run_all(
            reprocess_reason=reprocess_reason,
            max_batches_per_table=max_batches_per_table,
        )
        return {
            'reprocess_reason': reprocess_reason,
            'max_batches_per_table': max_batches_per_table,
            'normalization': normalization_result,
            'market_derivation': market_derivation_result,
            'caught_up': bool(normalization_result.get('caught_up', False))
            and bool(market_derivation_result.get('caught_up', False)),
        }
