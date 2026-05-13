import mysql.connector

class MysqlConnectionFactory:
    def connect_from_app_config(self, config):
        return mysql.connector.connect(
            host=config.database_host,
            port=config.database_port,
            database=config.database_name,
            user=config.database_username,
            password=config.database_password,
            autocommit=True,
            connection_timeout=getattr(config, 'database_connection_timeout_seconds', 5),
            read_timeout=getattr(config, 'database_read_timeout_seconds', 30),
            write_timeout=getattr(config, 'database_write_timeout_seconds', 30),
            use_pure=True,
        )
