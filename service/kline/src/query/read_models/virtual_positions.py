class VirtualPositionsReadModel:
    def __init__(
        self,
        *,
        projection_repository,
        live_payload_api,
        swap_base_url,
        post,
        pool_catalog_loader=None,
    ):
        self.projection_repository = projection_repository
        self.live_payload_api = live_payload_api
        self.swap_base_url = swap_base_url
        self.post = post
        self.pool_catalog_loader = pool_catalog_loader

    async def enrich_positions(
        self,
        *,
        owner: str,
        status: str,
        positions: list[dict],
    ) -> list[dict]:
        existing = list(positions)
        existing_keys = {
            (str(position.get('pool_application')), int(position.get('pool_id')))
            for position in existing
            if position.get('pool_application') is not None and position.get('pool_id') is not None
        }

        candidate_histories = await self._load_candidate_histories(owner=owner)
        if candidate_histories is None:
            return existing

        for candidate in candidate_histories:
            key = (str(candidate['pool_application']), int(candidate['pool_id']))
            if key in existing_keys:
                continue

            payload = await self.live_payload_api.fetch_payload(
                {
                    'owner': owner,
                    'pool_application': candidate['pool_application'],
                },
                self.swap_base_url,
                post=self.post,
            )
            payload_data = (payload or {}).get('data') or {}
            liquidity = payload_data.get('liquidity') or {}
            liquidity_value = liquidity.get('liquidity')
            if liquidity_value in (None, '', '0', '0.0'):
                continue
            if not bool(payload_data.get('virtualInitialLiquidity')):
                continue

            synthesized = dict(candidate)
            synthesized['status'] = 'active'
            synthesized['current_liquidity'] = str(liquidity_value)
            synthesized['added_liquidity'] = str(liquidity_value)
            synthesized['removed_liquidity'] = '0'
            synthesized['add_tx_count'] = max(int(candidate.get('add_tx_count') or 0), 1)
            synthesized['remove_tx_count'] = 0
            synthesized['closed_at'] = None
            synthesized['position_kind'] = 'virtual_initial_liquidity'
            synthesized['is_virtual_position'] = True
            existing.append(synthesized)
            existing_keys.add(key)

        normalized_status = (status or 'active').lower()
        if normalized_status in {'active', 'closed'}:
            existing = [position for position in existing if position.get('status') == normalized_status]
        existing.sort(
            key=lambda row: (
                -(row.get('closed_at') if normalized_status == 'closed' else row.get('updated_at') or 0),
                row.get('pool_id') or 0,
            ),
        )
        return existing

    async def _load_candidate_histories(self, *, owner: str) -> list[dict] | None:
        candidate_histories = self.projection_repository.get_owner_candidate_histories(owner=owner)
        if candidate_histories:
            return candidate_histories
        if self.pool_catalog_loader is None:
            return candidate_histories
        pools = await self.pool_catalog_loader()
        return [self._candidate_from_catalog_pool(pool, owner=owner) for pool in pools]

    def _candidate_from_catalog_pool(self, pool: object, *, owner: str) -> dict:
        if isinstance(pool, dict):
            pool_application = self._pool_application_from_catalog_dict(pool.get('poolApplication'))
            pool_id = int(pool.get('poolId'))
            token_0 = pool.get('token0')
            token_1 = pool.get('token1') or 'TLINERA'
        else:
            pool_application = f'{pool.pool_application.chain_id}:{pool.pool_application.owner}'
            pool_id = int(pool.pool_id)
            token_0 = pool.token_0
            token_1 = pool.token_1 or 'TLINERA'
        return {
            'pool_application': pool_application,
            'pool_id': pool_id,
            'token_0': token_0,
            'token_1': token_1,
            'owner': owner,
            'opened_at': None,
            'updated_at': 0,
            'add_tx_count': 0,
        }

    def _pool_application_from_catalog_dict(self, payload: object) -> str:
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            chain_id = payload.get('chain_id')
            owner = payload.get('owner')
            if chain_id and owner:
                return f'{chain_id}:{owner}'
        raise RuntimeError('invalid_pool_application_catalog_payload')
