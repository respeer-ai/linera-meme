from dataclasses import dataclass


@dataclass(frozen=True)
class MarketDataEvent:
    event_type: str
    pool_application: str | None = None
    pool_id: int | None = None
    token_reversed: bool | None = None
    interval: str | None = None
    transaction_id: int | None = None
    event_time_ms: int | None = None
    owner: str | None = None
    updated_at_ms: int | None = None

    TYPE_SETTLED_TRADE = 'settled_trade'
    TYPE_SETTLED_LIQUIDITY_CHANGE = 'settled_liquidity_change'
    TYPE_CANDLE_FINALIZED = 'candle_finalized'
    TYPE_PROJECTION_REBUILT = 'projection_rebuilt'
    TYPE_RANGE_INVALIDATED = 'range_invalidated'
