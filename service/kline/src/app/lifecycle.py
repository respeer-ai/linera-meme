class AppLifecycle:
    async def startup(self, container: dict[str, object]) -> None:
        raw_repository = container.get('raw_repository')
        if raw_repository is not None and hasattr(raw_repository, 'ensure_schema'):
            raw_repository.ensure_schema()
        application_registry_repository = container.get('application_registry_repository')
        if application_registry_repository is not None and hasattr(application_registry_repository, 'ensure_schema'):
            application_registry_repository.ensure_schema()
        application_registry = container.get('application_registry')
        config = container.get('config')
        if application_registry is not None and hasattr(application_registry, 'seed_from_config') and config is not None:
            application_registry.seed_from_config(config)
        catch_up_driver = container.get('catch_up_driver')
        if (
            config is not None
            and getattr(config, 'catch_up_on_startup', False)
            and catch_up_driver is not None
            and hasattr(catch_up_driver, 'run_once')
        ):
            await catch_up_driver.run_once()
        notification_listener = container.get('notification_listener')
        if notification_listener is not None and hasattr(notification_listener, 'start'):
            await notification_listener.start()

    async def shutdown(self, container: dict[str, object]) -> None:
        notification_listener = container.get('notification_listener')
        if notification_listener is not None and hasattr(notification_listener, 'stop'):
            await notification_listener.stop()
        connection = container.get('connection')
        if connection is not None and hasattr(connection, 'close'):
            connection.close()
