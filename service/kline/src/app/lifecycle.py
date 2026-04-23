class AppLifecycle:
    async def startup(self, container: dict[str, object]) -> None:
        raw_repository = container.get('raw_repository')
        if raw_repository is not None and hasattr(raw_repository, 'ensure_schema'):
            raw_repository.ensure_schema()

    async def shutdown(self, container: dict[str, object]) -> None:
        connection = container.get('connection')
        if connection is not None and hasattr(connection, 'close'):
            connection.close()
