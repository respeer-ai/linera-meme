import mysql.connector

class MysqlConnectionFactory:
    def connect_from_app_config(self, config):
        return mysql.connector.connect(
            host=config.database_host,
            port=config.database_port,
            database=config.database_name,
            user=config.database_username,
            password=config.database_password,
        )
