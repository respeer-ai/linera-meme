from dataclasses import dataclass

import mysql.connector


@dataclass(slots=True)
class MysqlConnectionConfig:
    host: str
    port: str
    database: str
    username: str
    password: str


def connect(config: MysqlConnectionConfig):
    return mysql.connector.connect(
        host=config.host,
        port=config.port,
        database=config.database,
        user=config.username,
        password=config.password,
    )

