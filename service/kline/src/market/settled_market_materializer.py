from market.claim_balance_deriver import ClaimBalanceDeriver
from market.claim_balance_correlation_deriver import ClaimBalanceCorrelationDeriver
from market.settled_output_batch_factory import SettledOutputBatchFactory


class SettledMarketMaterializer:
    def __init__(
        self,
        *,
        settled_market_deriver,
        settled_trade_repository,
        settled_liquidity_change_repository,
        claim_balance_projection_repository=None,
        claim_balance_deriver=None,
        claim_balance_correlation_deriver=None,
        pool_catalog_repository=None,
        normalized_event_repository=None,
        position_metrics_snapshot_materializer=None,
        settled_output_batch_factory=None,
    ):
        self.settled_market_deriver = settled_market_deriver
        self.settled_trade_repository = settled_trade_repository
        self.settled_liquidity_change_repository = settled_liquidity_change_repository
        self.claim_balance_projection_repository = claim_balance_projection_repository
        self.claim_balance_deriver = claim_balance_deriver or ClaimBalanceDeriver()
        self.claim_balance_correlation_deriver = (
            claim_balance_correlation_deriver
            or ClaimBalanceCorrelationDeriver(
                pool_catalog_repository=pool_catalog_repository,
                normalized_event_repository=normalized_event_repository,
            )
        )
        self.position_metrics_snapshot_materializer = position_metrics_snapshot_materializer
        self.settled_output_batch_factory = (
            settled_output_batch_factory
            or SettledOutputBatchFactory()
        )

    def materialize_item(self, event: dict[str, object]) -> dict[str, object]:
        derived = self._derive_item(event)
        self._persist_outputs(derived['settled_outputs'])
        return derived

    def materialize_batch(self, events: list[dict[str, object]]) -> list[dict[str, object]]:
        correlation = self.claim_balance_correlation_deriver.derive_batch(events)
        derived_batch = [
            self._derive_item(
                event,
                correlated_outputs=correlation['outputs_by_event_id'].get(
                    event['normalized_event_id'],
                    [],
                ),
                resolved_event_ids=correlation['resolved_event_ids'],
            )
            for event in events
        ]
        outputs = []
        for derived in derived_batch:
            outputs.extend(derived['settled_outputs'])
        outputs.extend(correlation['batch_outputs'])
        self._persist_outputs(outputs)
        return derived_batch

    def _derive_item(
        self,
        event: dict[str, object],
        *,
        correlated_outputs: list[dict[str, object]] | None = None,
        resolved_event_ids: set[str] | None = None,
    ) -> dict[str, object]:
        market_derived = self.settled_market_deriver.derive_item(event)
        claim_derived = self.claim_balance_deriver.derive_item(event)
        claim_outputs = self.claim_balance_correlation_deriver.filter_resolved_diagnostics(
            list(claim_derived['settled_outputs']),
            resolved_event_ids=resolved_event_ids or set(),
        )
        claim_outputs.extend(correlated_outputs or [])
        return {
            **market_derived,
            'settled_outputs': list(market_derived['settled_outputs']) + claim_outputs,
        }

    def _persist_outputs(self, outputs: list[dict[str, object]]) -> None:
        output_batch = self.settled_output_batch_factory.build(outputs)
        trades = output_batch.trades()
        liquidity_changes = output_batch.liquidity_changes()
        claim_balance_deltas = output_batch.claim_balance_deltas()
        claim_balance_diagnostics = output_batch.claim_balance_diagnostics()
        self.settled_trade_repository.upsert_settled_trades(trades)
        self.settled_liquidity_change_repository.upsert_settled_liquidity_changes(
            liquidity_changes
        )
        if self.claim_balance_projection_repository is not None:
            self.claim_balance_projection_repository.upsert_claim_balance_deltas(
                claim_balance_deltas
            )
            self.claim_balance_projection_repository.upsert_claim_balance_diagnostics(
                claim_balance_diagnostics
            )
        if self.position_metrics_snapshot_materializer is not None:
            self.position_metrics_snapshot_materializer.materialize_output_batch(
                output_batch
            )
