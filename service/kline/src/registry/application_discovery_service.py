from registry.application_registry import ApplicationRegistry


class ApplicationDiscoveryService:
    def __init__(
        self,
        *,
        application_registry: ApplicationRegistry,
        swap_catalog_client=None,
        swap_application_id: str | None = None,
        proxy_catalog_client=None,
        proxy_application_id: str | None = None,
    ):
        self.application_registry = application_registry
        self.swap_catalog_client = swap_catalog_client
        self.swap_application_id = swap_application_id
        self.proxy_catalog_client = proxy_catalog_client
        self.proxy_application_id = proxy_application_id

    async def discover_all(self) -> list[dict]:
        discovered = []
        discovered.extend(await self._discover_pool_applications_from_swap())
        discovered.extend(await self._discover_meme_applications_from_proxy())
        return discovered

    async def _discover_pool_applications_from_swap(self) -> list[dict]:
        if self.swap_catalog_client is None:
            return []
        pools = await self.swap_catalog_client.list_pools()
        discovered = []
        for pool in pools:
            pool_application = pool.get('poolApplication') or {}
            owner = pool_application.get('owner')
            chain_id = pool_application.get('chain_id')
            if owner is None or chain_id is None:
                continue
            discovered.append(
                self.application_registry.discover_application(
                    application_id=str(owner),
                    app_type='pool',
                    chain_id=str(chain_id),
                    creator_chain_id=self.swap_catalog_client.chain_id,
                    parent_application_id=self.swap_application_id,
                    discovered_from=ApplicationRegistry.SOURCE_SWAP_SERVICE,
                    metadata_json={
                        'pool_id': pool.get('poolId'),
                        'token_0': pool.get('token0'),
                        'token_1': pool.get('token1'),
                    },
                )
            )
        return discovered

    async def _discover_meme_applications_from_proxy(self) -> list[dict]:
        if self.proxy_catalog_client is None:
            return []
        meme_applications = await self.proxy_catalog_client.list_meme_applications()
        discovered = []
        for meme_application in meme_applications:
            token = meme_application.get('token')
            chain_id = meme_application.get('chainId')
            if token is None or chain_id is None:
                continue
            discovered.append(
                self.application_registry.discover_application(
                    application_id=str(token),
                    app_type='meme',
                    chain_id=str(chain_id),
                    creator_chain_id=self.proxy_catalog_client.chain_id,
                    parent_application_id=self.proxy_application_id,
                    discovered_from=ApplicationRegistry.SOURCE_PROXY_SERVICE,
                    metadata_json={},
                )
            )
        return discovered
