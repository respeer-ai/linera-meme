class MarketDerivationWorker:
    def __init__(
        self,
        *,
        settled_market_materializer,
        processing_cursor_repository,
        market_data_event_sink=None,
        business_freshness_service=None,
        cursor_name: str = 'layer3_market_deriver',
        cursor_scope: str = 'derive',
    ):
        self.settled_market_materializer = settled_market_materializer
        self.processing_cursor_repository = processing_cursor_repository
        self.market_data_event_sink = market_data_event_sink
        self.business_freshness_service = business_freshness_service
        self.cursor_name = cursor_name
        self.cursor_scope = cursor_scope

    def process_items(
        self,
        items: list[dict],
        *,
        partition_key: str = 'global',
        reprocess_reason: str | None = None,
    ) -> dict[str, object]:
        last_sequence = self._last_sequence(items)
        last_block_hash = self._last_block_hash(items)
        self.processing_cursor_repository.mark_attempt(
            cursor_name=self.cursor_name,
            cursor_scope=self.cursor_scope,
            partition_key=partition_key,
            last_sequence=last_sequence,
            last_block_hash=last_block_hash,
        )
        try:
            derivation_batch = self.settled_market_materializer.materialize_batch(items)
        except Exception as error:
            self.processing_cursor_repository.mark_failure(
                cursor_name=self.cursor_name,
                cursor_scope=self.cursor_scope,
                partition_key=partition_key,
                last_sequence=last_sequence,
                last_block_hash=last_block_hash,
                error_text=str(error),
            )
            raise
        self.processing_cursor_repository.mark_success(
            cursor_name=self.cursor_name,
            cursor_scope=self.cursor_scope,
            partition_key=partition_key,
            last_sequence=last_sequence,
            last_block_hash=last_block_hash,
        )
        if self.market_data_event_sink is not None:
            self.market_data_event_sink.publish_derivation_batch(derivation_batch)
        self._check_business_freshness(derivation_batch)
        return {
            'cursor_name': self.cursor_name,
            'cursor_scope': self.cursor_scope,
            'partition_key': partition_key,
            'processed_count': len(items),
            'derived_output_count': sum(
                len(item['settled_outputs'])
                for item in derivation_batch
            ),
            'last_sequence': last_sequence,
            'last_block_hash': last_block_hash,
            'reprocess_reason': reprocess_reason,
            'derivation_batch': derivation_batch,
        }

    def _last_sequence(self, items: list[dict]) -> str | None:
        if not items:
            return None
        value = items[-1].get('raw_fact_id')
        if value is None:
            value = items[-1].get('normalized_event_id')
        if value is None:
            return None
        return str(value)

    def _last_block_hash(self, items: list[dict]) -> str | None:
        if not items:
            return None
        candidate = items[-1].get('target_block_hash') or items[-1].get('source_block_hash')
        if candidate is None:
            return None
        return str(candidate)

    def _check_business_freshness(self, derivation_batch) -> None:
        if self.business_freshness_service is None:
            return
        pool_applications = self._pool_applications(derivation_batch)
        if not pool_applications:
            self._safe_business_freshness_check(pool_application=None)
            return
        for pool_application in pool_applications:
            self._safe_business_freshness_check(pool_application=pool_application)

    def _safe_business_freshness_check(self, *, pool_application: str | None) -> None:
        try:
            self.business_freshness_service.check(
                pool_application=pool_application,
                trigger='market_derivation',
            )
        except Exception as error:
            print(f'Failed check business freshness after market derivation: {error}')

    def _pool_applications(self, derivation_batch) -> tuple[str, ...]:
        pool_applications = []
        for item in derivation_batch:
            for output in item.get('settled_outputs', []):
                pool_application = output.get('pool_application_id')
                if pool_application and pool_application not in pool_applications:
                    pool_applications.append(pool_application)
        return tuple(pool_applications)
