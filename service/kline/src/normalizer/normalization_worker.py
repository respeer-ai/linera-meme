class NormalizationWorker:
    def __init__(
        self,
        *,
        decode_scheduler,
        normalized_event_materializer,
        processing_cursor_repository,
        cursor_name: str = 'layer2_normalizer',
        cursor_scope: str = 'normalize',
    ):
        self.decode_scheduler = decode_scheduler
        self.normalized_event_materializer = normalized_event_materializer
        self.processing_cursor_repository = processing_cursor_repository
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
            decoded_batch = self.decode_scheduler.decode_batch(
                items,
                reprocess_reason=reprocess_reason,
            )
            normalized_batch = self.normalized_event_materializer.materialize_batch(
                decoded_batch
            )
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
        return {
            'cursor_name': self.cursor_name,
            'cursor_scope': self.cursor_scope,
            'partition_key': partition_key,
            'processed_count': len(items),
            'normalized_event_count': sum(
                len(item['normalized_events'])
                for item in normalized_batch
            ),
            'last_sequence': last_sequence,
            'last_block_hash': last_block_hash,
            'reprocess_reason': reprocess_reason,
            'normalized_batch': normalized_batch,
        }

    def _last_sequence(self, items: list[dict]) -> str | None:
        if not items:
            return None
        value = items[-1].get('raw_fact_id')
        if value is None:
            return None
        return str(value)

    def _last_block_hash(self, items: list[dict]) -> str | None:
        if not items:
            return None
        candidate = (
            items[-1].get('target_block_hash')
            or items[-1].get('source_block_hash')
            or items[-1].get('block_hash')
        )
        if candidate is None:
            return None
        return str(candidate)

