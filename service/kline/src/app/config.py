from dataclasses import dataclass


@dataclass(slots=True)
class DatabaseConfig:
    host: str
    port: str
    name: str
    username: str
    password: str


@dataclass(slots=True)
class KlineAppConfig:
    database: DatabaseConfig
    swap_host: str | None = None
    swap_chain_id: str | None = None
    swap_application_id: str | None = None

