from app.config import KlineAppConfig
from storage.mysql.connection import MysqlConnectionFactory
from storage.mysql.raw_repo import RawRepository


class AppBootstrap:
    def build_container(self, config: KlineAppConfig) -> dict[str, object]:
        connection = MysqlConnectionFactory().connect_from_app_config(config)
        raw_repository = RawRepository(connection)
        return {
            'config': config,
            'connection': connection,
            'raw_repository': raw_repository,
        }
