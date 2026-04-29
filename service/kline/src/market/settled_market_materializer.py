from market.settled_market_result import SettledMarketResult


class SettledMarketMaterializer:
    def __init__(
        self,
        *,
        settled_market_deriver,
        settled_trade_repository,
        settled_liquidity_change_repository,
        position_metrics_snapshot_materializer=None,
    ):
        self.settled_market_deriver = settled_market_deriver
        self.settled_trade_repository = settled_trade_repository
        self.settled_liquidity_change_repository = settled_liquidity_change_repository
        self.position_metrics_snapshot_materializer = position_metrics_snapshot_materializer

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
        trades = []
        liquidity_changes = []
        for output in outputs:
            output_type = output.get('settled_output_type')
            if output_type == SettledMarketResult.OUTPUT_SETTLED_TRADE:
                trades.append(output)
                continue
            if output_type == SettledMarketResult.OUTPUT_SETTLED_LIQUIDITY_CHANGE:
                liquidity_changes.append(output)
        self.settled_trade_repository.upsert_settled_trades(trades)
        self.settled_liquidity_change_repository.upsert_settled_liquidity_changes(
            liquidity_changes
        )
        if self.position_metrics_snapshot_materializer is not None:
            self.position_metrics_snapshot_materializer.materialize_outputs(outputs)
