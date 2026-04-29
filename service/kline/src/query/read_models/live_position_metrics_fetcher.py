class LivePositionMetricsFetcher:
    def __init__(
        self,
        *,
        repository,
        pool_application_client,
        parse_owner_account,
        enrich_payload,
        snapshot_fast_path=None,
        snapshot_shadow_evaluator=None,
    ):
        self.repository = repository
        self.pool_application_client = pool_application_client
        self.parse_owner_account = parse_owner_account
        self.enrich_payload = enrich_payload
        self.snapshot_fast_path = snapshot_fast_path
        self.snapshot_shadow_evaluator = snapshot_shadow_evaluator

    async def __call__(self, position: dict):
        owner = self.parse_owner_account(position['owner'])
        payload = await self.pool_application_client.get_position_metrics_payload(
            pool_application=position['pool_application'],
            owner=owner,
        )
        snapshot_inputs = None
        if hasattr(self.repository, 'get_snapshot_inputs'):
            snapshot_inputs = self.repository.get_snapshot_inputs(
                owner=position['owner'],
                pool_application_id=position['pool_application'],
                status=position.get('status') or 'active',
            )
        if self.snapshot_fast_path is not None:
            fast_path_payload = self.snapshot_fast_path.resolve(
                position=position,
                payload=payload,
                position_basis_snapshot=(snapshot_inputs or {}).get('position_basis_snapshot'),
                pool_state_snapshot=(snapshot_inputs or {}).get('pool_state_snapshot'),
            )
            if fast_path_payload is not None:
                return fast_path_payload
        liquidity_history = self.repository.get_position_liquidity_history(
            owner=position['owner'],
            pool_application=position['pool_application'],
            pool_id=position['pool_id'],
        )
        pool_transaction_history = self.repository.get_pool_transaction_history(
            pool_application=position['pool_application'],
            pool_id=position['pool_id'],
        )
        live_metrics = self.enrich_payload(
            position,
            payload,
            liquidity_history=liquidity_history,
            pool_transaction_history=pool_transaction_history,
            pool_swap_count_since_open=self.repository.get_pool_swap_count_since(
                pool_application=position['pool_application'],
                pool_id=position['pool_id'],
                created_at=position['opened_at'],
            ),
            pool_history_gap_summary=self.repository.get_pool_transaction_gap_summary(
                pool_application=position['pool_application'],
                pool_id=position['pool_id'],
            ),
            position_basis_snapshot=(snapshot_inputs or {}).get('position_basis_snapshot'),
            pool_state_snapshot=(snapshot_inputs or {}).get('pool_state_snapshot'),
        )
        if self.snapshot_shadow_evaluator is None:
            return live_metrics
        return {
            'live_metrics': live_metrics,
            'snapshot_shadow': self.snapshot_shadow_evaluator.evaluate(
                position=position,
                live_metrics=live_metrics,
                liquidity_history=liquidity_history,
                pool_transaction_history=pool_transaction_history,
                position_basis_snapshot=(snapshot_inputs or {}).get('position_basis_snapshot'),
                pool_state_snapshot=(snapshot_inputs or {}).get('pool_state_snapshot'),
            ),
        }
