from market.claim_balance_deriver import ClaimBalanceDeriver
from market.claim_balance_correlation_deriver import ClaimBalanceCorrelationDeriver
from market.settled_output_batch_factory import SettledOutputBatchFactory


class SettledMarketMaterializer:
    VIRTUAL_INITIAL_LIQUIDITY = 'virtual_initial_liquidity'

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
        virtual_initial_transaction_ids = self._virtual_initial_transaction_ids(events)
        derived_batch = [
            self._derive_item(
                event,
                correlated_outputs=correlation['outputs_by_event_id'].get(
                    event['normalized_event_id'],
                    [],
                ),
                resolved_event_ids=correlation['resolved_event_ids'],
                liquidity_semantics=(
                    self.VIRTUAL_INITIAL_LIQUIDITY
                    if str(event.get('normalized_event_id')) in virtual_initial_transaction_ids
                    else None
                ),
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
        liquidity_semantics: str | None = None,
    ) -> dict[str, object]:
        market_derived = self.settled_market_deriver.derive_item(
            event,
            liquidity_semantics=liquidity_semantics,
        )
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

    def _virtual_initial_transaction_ids(self, events: list[dict[str, object]]) -> set[str]:
        initialize_messages = self._pool_initialize_messages(events)
        if not initialize_messages:
            return set()
        initialize_blocks = {
            (str(message.get('application_id')), str(message.get('target_block_hash') or message.get('source_block_hash')))
            for message in initialize_messages
            if message.get('application_id') not in (None, '')
            and (message.get('target_block_hash') or message.get('source_block_hash')) not in (None, '')
        }
        if not initialize_blocks:
            return set()
        transaction_ids = set()
        for event in self._pool_new_transactions(events):
            key = (str(event.get('application_id')), str(event.get('source_cert_hash')))
            if key in initialize_blocks and self._pool_new_transaction_type(event) == 'AddLiquidity':
                transaction_ids.add(str(event['normalized_event_id']))
        return transaction_ids

    def _pool_initialize_messages(self, events: list[dict[str, object]]) -> list[dict[str, object]]:
        messages = [
            event
            for event in events
            if event.get('normalization_status') == 'observed'
            and event.get('event_family') == 'pool_initialize_liquidity_message_observed'
        ]
        messages.extend(self._repository_initialize_messages_for_new_transactions(events))
        return self._unique_events(messages)

    def _repository_initialize_messages_for_new_transactions(self, events: list[dict[str, object]]) -> list[dict[str, object]]:
        normalized_event_repository = getattr(
            self.claim_balance_correlation_deriver,
            'normalized_event_repository',
            None,
        )
        if normalized_event_repository is None:
            return []
        list_messages = getattr(
            normalized_event_repository,
            'list_pool_initialize_liquidity_messages',
            None,
        )
        if list_messages is None:
            return []
        messages = []
        for event in self._pool_new_transactions(events):
            source_cert_hash = event.get('source_cert_hash')
            if source_cert_hash in (None, ''):
                continue
            messages.extend(
                list_messages(
                    application_id=str(event['application_id']),
                    target_block_hash=str(source_cert_hash),
                )
            )
        return messages

    def _pool_new_transaction_type(self, event: dict[str, object]) -> str | None:
        transaction = (event.get('event_payload_json') or {}).get('decoded_payload_json', {}).get('transaction')
        if not isinstance(transaction, dict):
            return None
        value = transaction.get('transaction_type')
        return None if value is None else str(value)

    def _pool_new_transactions(self, events: list[dict[str, object]]) -> list[dict[str, object]]:
        return [
            event
            for event in events
            if event.get('normalization_status') == 'observed'
            and event.get('event_family') == 'pool_new_transaction_recorded'
        ]

    def _unique_events(self, events: list[dict[str, object]]) -> list[dict[str, object]]:
        unique = {}
        for event in events:
            event_id = event.get('normalized_event_id')
            if event_id is not None:
                unique[str(event_id)] = event
        return list(unique.values())

    def _persist_outputs(self, outputs: list[dict[str, object]]) -> None:
        output_batch = self.settled_output_batch_factory.build(outputs)
        trades = output_batch.trades()
        liquidity_changes = output_batch.liquidity_changes()
        claim_balance_deltas = output_batch.claim_balance_deltas()
        correlated_event_ids = {
            str(output['normalized_event_id'])
            for output in claim_balance_deltas
            if str(output.get('derivation_source') or '').startswith('correlated_')
        }
        claim_balance_diagnostics = [
            output
            for output in output_batch.claim_balance_diagnostics()
            if str(output.get('normalized_event_id')) not in correlated_event_ids
        ]
        self.settled_trade_repository.upsert_settled_trades(trades)
        self.settled_liquidity_change_repository.upsert_settled_liquidity_changes(
            liquidity_changes
        )
        if self.claim_balance_projection_repository is not None:
            self.claim_balance_projection_repository.delete_claim_balance_diagnostics_for_events(
                normalized_event_ids=correlated_event_ids,
                diagnostic_types={
                    self.claim_balance_correlation_deriver.CORRELATION_DIAGNOSTIC,
                    'ambiguous_new_transaction_correlation',
                    'missing_pool_token_metadata',
                },
            )
            self.claim_balance_projection_repository.delete_correlated_claim_balance_deltas_for_events(
                normalized_event_ids=correlated_event_ids,
            )
            self.claim_balance_projection_repository.upsert_claim_balance_deltas(
                claim_balance_deltas
            )
            self.claim_balance_projection_repository.upsert_claim_balance_diagnostics(
                claim_balance_diagnostics
            )
        if self.position_metrics_snapshot_materializer is not None:
            snapshot_summary = self.position_metrics_snapshot_materializer.materialize_output_batch(
                output_batch
            )
            if snapshot_summary and snapshot_summary.get('degraded'):
                error_text = snapshot_summary.get('error_text') or 'unknown snapshot materialization error'
                raise RuntimeError(f'position metrics snapshot materialization failed: {error_text}')
