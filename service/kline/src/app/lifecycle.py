class AppLifecycle:
    def ensure_schema(self, container: dict[str, object]) -> None:
        raw_repository = container.get('raw_repository')
        if raw_repository is not None and hasattr(raw_repository, 'ensure_schema'):
            raw_repository.ensure_schema()
        application_registry_repository = container.get('application_registry_repository')
        if application_registry_repository is not None and hasattr(application_registry_repository, 'ensure_schema'):
            application_registry_repository.ensure_schema()
        normalized_event_repository = container.get('normalized_event_repository')
        if normalized_event_repository is not None and hasattr(normalized_event_repository, 'ensure_schema'):
            normalized_event_repository.ensure_schema()
        settled_trade_repository = container.get('settled_trade_repository')
        if settled_trade_repository is not None and hasattr(settled_trade_repository, 'ensure_schema'):
            settled_trade_repository.ensure_schema()
        settled_liquidity_change_repository = container.get('settled_liquidity_change_repository')
        if (
            settled_liquidity_change_repository is not None
            and hasattr(settled_liquidity_change_repository, 'ensure_schema')
        ):
            settled_liquidity_change_repository.ensure_schema()
        position_state_snapshot_repository = container.get('position_state_snapshot_repository')
        if (
            position_state_snapshot_repository is not None
            and hasattr(position_state_snapshot_repository, 'ensure_schema')
        ):
            position_state_snapshot_repository.ensure_schema()
        pool_state_snapshot_repository = container.get('pool_state_snapshot_repository')
        if (
            pool_state_snapshot_repository is not None
            and hasattr(pool_state_snapshot_repository, 'ensure_schema')
        ):
            pool_state_snapshot_repository.ensure_schema()

    def seed_registry(self, container: dict[str, object]) -> None:
        application_registry = container.get('application_registry')
        config = container.get('config')
        if application_registry is not None and hasattr(application_registry, 'seed_from_config') and config is not None:
            application_registry.seed_from_config(config)

    async def discover_registry(self, container: dict[str, object]) -> None:
        application_discovery_service = container.get('application_discovery_service')
        if application_discovery_service is not None and hasattr(application_discovery_service, 'discover_all'):
            await application_discovery_service.discover_all()

    def sync_discovered_chain_ids(self, container: dict[str, object]) -> tuple[str, ...]:
        application_registry = container.get('application_registry')
        if application_registry is None or not hasattr(application_registry, 'list_known_applications'):
            return ()

        discovered_chain_ids = []
        for app_type in ('pool', 'meme'):
            applications = application_registry.list_known_applications(app_type=app_type, limit=1000)
            for application in applications:
                chain_id = application.get('chain_id')
                if chain_id is not None and str(chain_id).strip():
                    discovered_chain_ids.append(str(chain_id))

        if not discovered_chain_ids:
            return ()

        normalized_chain_ids = tuple(sorted(set(discovered_chain_ids)))
        for key in ('chain_event_processor', 'catch_up_driver'):
            component = container.get(key)
            if component is not None and hasattr(component, 'add_chain_ids'):
                component.add_chain_ids(normalized_chain_ids)

        notification_listener = container.get('notification_listener')
        if notification_listener is not None and hasattr(notification_listener, 'add_chain_ids'):
            return normalized_chain_ids
        return normalized_chain_ids

    async def run_startup_catch_up(self, container: dict[str, object]) -> None:
        config = container.get('config')
        catch_up_driver = container.get('catch_up_driver')
        if (
            config is not None
            and getattr(config, 'catch_up_on_startup', False)
            and catch_up_driver is not None
            and hasattr(catch_up_driver, 'run_once')
        ):
            await catch_up_driver.run_once()

    async def start_listener(self, container: dict[str, object]) -> None:
        notification_listener = container.get('notification_listener')
        if notification_listener is not None and hasattr(notification_listener, 'start'):
            await notification_listener.start()

    async def startup(self, container: dict[str, object]) -> None:
        self.ensure_schema(container)
        self.seed_registry(container)
        await self.run_startup_catch_up(container)
        await self.start_listener(container)

    async def stop_listener(self, container: dict[str, object]) -> None:
        notification_listener = container.get('notification_listener')
        if notification_listener is not None and hasattr(notification_listener, 'stop'):
            await notification_listener.stop()

    def close_connection(self, container: dict[str, object]) -> None:
        connection = container.get('connection')
        if connection is not None and hasattr(connection, 'close'):
            connection.close()

    async def shutdown(self, container: dict[str, object]) -> None:
        await self.stop_listener(container)
        self.close_connection(container)
