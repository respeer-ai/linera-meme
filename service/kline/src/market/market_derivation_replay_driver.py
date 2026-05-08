class MarketDerivationReplayDriver:
    def __init__(
        self,
        *,
        normalized_event_repository,
        processing_cursor_repository,
        market_derivation_worker,
        raw_tables: tuple[str, ...] = ('raw_posted_messages',),
        batch_limit: int = 100,
    ):
        self.normalized_event_repository = normalized_event_repository
        self.processing_cursor_repository = processing_cursor_repository
        self.market_derivation_worker = market_derivation_worker
        self.raw_tables = tuple(raw_tables)
        self.batch_limit = int(batch_limit)

    def run_once(
        self,
        *,
        raw_table: str,
        batch_limit: int | None = None,
        after_sequence: int | None = None,
        ignore_cursor: bool = False,
        reprocess_reason: str | None = None,
    ) -> dict[str, object]:
        partition_key = raw_table
        cursor = None
        effective_after_sequence = after_sequence
        if effective_after_sequence is None and not ignore_cursor:
            cursor = self.processing_cursor_repository.load_cursor(
                cursor_name=self.market_derivation_worker.cursor_name,
                partition_key=partition_key,
            )
            effective_after_sequence = self._parse_sequence(cursor)
        effective_limit = self.batch_limit if batch_limit is None else int(batch_limit)
        items = self.normalized_event_repository.list_market_derivation_candidates(
            raw_table=raw_table,
            after_sequence=effective_after_sequence,
            limit=effective_limit,
        )
        if not items:
            return {
                'raw_table': raw_table,
                'partition_key': partition_key,
                'cursor': cursor,
                'after_sequence': effective_after_sequence,
                'processed_count': 0,
                'caught_up': True,
            }
        result = self.market_derivation_worker.process_items(
            items,
            partition_key=partition_key,
            reprocess_reason=reprocess_reason,
        )
        return {
            'raw_table': raw_table,
            'partition_key': partition_key,
            'cursor': cursor,
            'after_sequence': effective_after_sequence,
            'processed_count': result['processed_count'],
            'derived_output_count': result['derived_output_count'],
            'last_sequence': result['last_sequence'],
            'caught_up': len(items) < effective_limit,
            'result': result,
        }

    def run_until_caught_up(
        self,
        *,
        raw_table: str,
        batch_limit: int | None = None,
        after_sequence: int | None = None,
        ignore_cursor: bool = False,
        reprocess_reason: str | None = None,
        max_batches: int | None = None,
    ) -> dict[str, object]:
        effective_max_batches = 1 if max_batches is None else int(max_batches)
        results = []
        total_processed_count = 0
        total_derived_output_count = 0
        for _ in range(effective_max_batches):
            result = self.run_once(
                raw_table=raw_table,
                batch_limit=batch_limit,
                after_sequence=after_sequence,
                ignore_cursor=ignore_cursor,
                reprocess_reason=reprocess_reason,
            )
            results.append(result)
            total_processed_count += int(result.get('processed_count', 0))
            total_derived_output_count += int(result.get('derived_output_count', 0))
            if result.get('caught_up'):
                break
            last_sequence = result.get('last_sequence')
            after_sequence = int(last_sequence) if last_sequence is not None else after_sequence
            ignore_cursor = False
        return {
            'raw_table': raw_table,
            'batch_count': len(results),
            'max_batches': effective_max_batches,
            'processed_count': total_processed_count,
            'derived_output_count': total_derived_output_count,
            'caught_up': bool(results[-1]['caught_up']) if results else True,
            'results': results,
        }

    def run_all(
        self,
        *,
        batch_limit: int | None = None,
        reprocess_reason: str | None = None,
        max_batches_per_table: int | None = None,
    ) -> dict[str, object]:
        results = []
        processed_count = 0
        derived_output_count = 0
        for raw_table in self.raw_tables:
            result = self.run_until_caught_up(
                raw_table=raw_table,
                batch_limit=batch_limit,
                reprocess_reason=reprocess_reason,
                max_batches=max_batches_per_table,
            )
            results.append(result)
            processed_count += int(result.get('processed_count', 0))
            derived_output_count += int(result.get('derived_output_count', 0))
        return {
            'raw_tables': list(self.raw_tables),
            'table_count': len(self.raw_tables),
            'processed_count': processed_count,
            'derived_output_count': derived_output_count,
            'results': results,
        }

    def run_all_until_caught_up(
        self,
        *,
        batch_limit: int | None = None,
        reprocess_reason: str | None = None,
    ) -> dict[str, object]:
        results = []
        processed_count = 0
        derived_output_count = 0
        for raw_table in self.raw_tables:
            result = self._run_table_until_caught_up(
                raw_table=raw_table,
                batch_limit=batch_limit,
                reprocess_reason=reprocess_reason,
            )
            results.append(result)
            processed_count += int(result.get('processed_count', 0))
            derived_output_count += int(result.get('derived_output_count', 0))
        return {
            'raw_tables': list(self.raw_tables),
            'table_count': len(self.raw_tables),
            'processed_count': processed_count,
            'derived_output_count': derived_output_count,
            'caught_up': all(result.get('caught_up', False) for result in results),
            'results': results,
        }

    def _run_table_until_caught_up(
        self,
        *,
        raw_table: str,
        batch_limit: int | None = None,
        reprocess_reason: str | None = None,
    ) -> dict[str, object]:
        results = []
        total_processed_count = 0
        total_derived_output_count = 0
        while True:
            result = self.run_once(
                raw_table=raw_table,
                batch_limit=batch_limit,
                reprocess_reason=reprocess_reason,
            )
            results.append(result)
            total_processed_count += int(result.get('processed_count', 0))
            total_derived_output_count += int(result.get('derived_output_count', 0))
            if result.get('caught_up'):
                return {
                    'raw_table': raw_table,
                    'batch_count': len(results),
                    'processed_count': total_processed_count,
                    'derived_output_count': total_derived_output_count,
                    'caught_up': True,
                    'results': results,
                }

    def _parse_sequence(self, cursor: dict | None) -> int | None:
        if cursor is None:
            return None
        last_sequence = cursor.get('last_sequence')
        if last_sequence in (None, ''):
            return None
        return int(last_sequence)
