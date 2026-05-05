class KlineObservabilityDebugService:
    def __init__(
        self,
        *,
        observability_facade,
    ):
        self._observability_facade = observability_facade

    async def run_catch_up(self, *, chain_id: str | None, max_blocks: int | None):
        if max_blocks is not None and max_blocks <= 0:
            raise ValueError('max_blocks must be positive')
        if self._observability_facade is None:
            raise RuntimeError('Observability runtime is not configured')
        return await self._observability_facade.run_catch_up(
            chain_id=chain_id,
            max_blocks=max_blocks,
        )

    async def run_normalization_replay(
        self,
        *,
        raw_table: str | None,
        batch_limit: int | None,
        max_batches: int | None,
        reprocess_reason: str | None,
    ):
        if batch_limit is not None and batch_limit <= 0:
            raise ValueError('batch_limit must be positive')
        if max_batches is not None and max_batches <= 0:
            raise ValueError('max_batches must be positive')
        if raw_table is not None and raw_table not in {
            'raw_operations',
            'raw_posted_messages',
            'raw_events',
        }:
            raise ValueError('raw_table must be one of raw_operations, raw_posted_messages, raw_events')
        if self._observability_facade is None:
            raise RuntimeError('Observability runtime is not configured')
        return await self._observability_facade.run_normalization_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )

    async def run_market_derivation_replay(
        self,
        *,
        raw_table: str | None,
        batch_limit: int | None,
        max_batches: int | None,
        reprocess_reason: str | None,
    ):
        if batch_limit is not None and batch_limit <= 0:
            raise ValueError('batch_limit must be positive')
        if max_batches is not None and max_batches <= 0:
            raise ValueError('max_batches must be positive')
        if raw_table is not None and raw_table not in {'raw_posted_messages'}:
            raise ValueError('raw_table must be one of raw_posted_messages')
        if self._observability_facade is None:
            raise RuntimeError('Observability runtime is not configured')
        return await self._observability_facade.run_market_derivation_replay(
            raw_table=raw_table,
            batch_limit=batch_limit,
            max_batches=max_batches,
            reprocess_reason=reprocess_reason,
        )

    def get_debug_observability(
        self,
        *,
        chain_ids: str | None,
        run_statuses: str | None,
        anomaly_statuses: str | None,
        limit: int,
    ):
        if limit <= 0:
            raise ValueError('limit must be positive')

        parsed_chain_ids = tuple(
            chain_id.strip()
            for chain_id in (chain_ids or '').split(',')
            if chain_id.strip()
        )
        parsed_run_statuses = tuple(
            status.strip()
            for status in (run_statuses or '').split(',')
            if status.strip()
        )
        parsed_anomaly_statuses = tuple(
            status.strip()
            for status in (anomaly_statuses or '').split(',')
            if status.strip()
        )

        if self._observability_facade is None:
            return {
                'status': {
                    'configured': False,
                    'state': 'disabled',
                    'ready': False,
                    'last_error': 'observability is not configured',
                    'last_transition_at': None,
                    'starting_in_background': False,
                    'components': {},
                },
                'chain_ids': list(parsed_chain_ids),
                'run_statuses': list(parsed_run_statuses),
                'anomaly_statuses': list(parsed_anomaly_statuses),
                'cursors': [],
                'recent_runs': [],
                'anomalies': [],
            }
        return self._observability_facade.get_debug_observability(
            chain_ids=parsed_chain_ids,
            run_statuses=parsed_run_statuses,
            anomaly_statuses=parsed_anomaly_statuses,
            limit=limit,
        )

    async def recover_observability(self):
        if self._observability_facade is None:
            return {
                'recovered': False,
                'status': {
                    'configured': False,
                    'state': 'disabled',
                    'ready': False,
                    'last_error': 'observability is not configured',
                    'last_transition_at': None,
                    'starting_in_background': False,
                    'recovery_allowed': False,
                    'components': {},
                },
            }
        return await self._observability_facade.recover()
