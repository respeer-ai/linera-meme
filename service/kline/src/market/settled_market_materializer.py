from market.settled_output_batch_factory import SettledOutputBatchFactory


class SettledMarketMaterializer:
    def __init__(
        self,
        *,
        settled_market_deriver,
        settled_trade_repository,
        settled_liquidity_change_repository,
        position_metrics_snapshot_materializer=None,
        settled_output_batch_factory=None,
    ):
        self.settled_market_deriver = settled_market_deriver
        self.settled_trade_repository = settled_trade_repository
        self.settled_liquidity_change_repository = settled_liquidity_change_repository
        self.position_metrics_snapshot_materializer = position_metrics_snapshot_materializer
        self.settled_output_batch_factory = (
            settled_output_batch_factory
            or SettledOutputBatchFactory()
        )

    def materialize_item(self, event: dict[str, object]) -> dict[str, object]:
        derived = self.settled_market_deriver.derive_item(event)
        self._persist_outputs(derived['settled_outputs'])
        return derived

    def materialize_batch(self, events: list[dict[str, object]]) -> list[dict[str, object]]:
        derived_batch = self.settled_market_deriver.derive_batch(events)
        outputs = []
        for derived in derived_batch:
            outputs.extend(derived['settled_outputs'])
        self._persist_outputs(outputs)
        return derived_batch

    def _persist_outputs(self, outputs: list[dict[str, object]]) -> None:
        output_batch = self.settled_output_batch_factory.build(outputs)
        trades = output_batch.trades()
        liquidity_changes = output_batch.liquidity_changes()
        self.settled_trade_repository.upsert_settled_trades(trades)
        self.settled_liquidity_change_repository.upsert_settled_liquidity_changes(
            liquidity_changes
        )
        if self.position_metrics_snapshot_materializer is not None:
            self.position_metrics_snapshot_materializer.materialize_output_batch(
                output_batch
            )
