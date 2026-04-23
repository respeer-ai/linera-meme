from dataclasses import dataclass


@dataclass(slots=True)
class KlineAppConfig:
    database_host: str
    database_port: str
    database_name: str
    database_username: str
    database_password: str
    swap_host: str | None = None
    swap_chain_id: str | None = None
    swap_application_id: str | None = None
