from dataclasses import dataclass


@dataclass(slots=True)
class KlineAppConfig:
    database_host: str
    database_port: str
    database_name: str
    database_username: str
    database_password: str
    chain_graphql_url: str | None = None
    chain_graphql_ws_url: str | None = None
    chain_graphql_header_batch_limit: int = 50
    catch_up_chain_ids: tuple[str, ...] = ()
    catch_up_max_blocks_per_chain: int = 50
    catch_up_on_startup: bool = True
    notification_reconnect_delay_seconds: float = 1.0
    swap_host: str | None = None
    swap_chain_id: str | None = None
    swap_application_id: str | None = None
