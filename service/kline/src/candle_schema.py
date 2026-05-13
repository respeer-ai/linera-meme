from dataclasses import dataclass


INTERVAL_BUCKET_MS = {
    '1min': 60_000,
    '5min': 300_000,
    '10min': 600_000,
    '15min': 900_000,
    '1h': 3_600_000,
    '4h': 14_400_000,
    '1D': 86_400_000,
    '1W': 604_800_000,
    '1ME': 2_592_000_000,
}

API_TO_STORAGE_INTERVAL = {
    '1m': '1min',
    '1min': '1min',
    '5m': '5min',
    '5min': '5min',
    '10m': '10min',
    '10min': '10min',
    '15m': '15min',
    '15min': '15min',
    '1h': '1h',
    '4h': '4h',
    '1d': '1D',
    '1w': '1W',
    '1ME': '1ME',
    '1D': '1D',
    '1W': '1W',
}

STORAGE_TO_API_INTERVAL = {
    '1min': '1min',
    '5min': '5min',
    '10min': '10min',
    '15min': '15min',
    '1h': '1h',
    '4h': '4h',
    '1D': '1d',
    '1W': '1w',
    '1ME': '1ME',
}


@dataclass(frozen=True)
class CandleBucketKey:
    pool_application: str
    pool_id: int
    token_reversed: bool
    interval: str
    bucket_start_ms: int


@dataclass(frozen=True)
class CandleUpdate:
    transaction_id: int
    created_at_ms: int
    price: float
    base_volume: float
    quote_volume: float


@dataclass(frozen=True)
class CandleState:
    open: float
    high: float
    low: float
    close: float
    base_volume: float
    quote_volume: float
    trade_count: int
    first_trade_id: int
    last_trade_id: int
    first_trade_at_ms: int
    last_trade_at_ms: int


def normalize_interval_for_storage(interval: str) -> str:
    normalized = API_TO_STORAGE_INTERVAL.get(interval)
    if normalized is None:
        raise ValueError(f'Unsupported interval: {interval}')
    return normalized


def normalize_interval_for_api(interval: str) -> str:
    if interval in API_TO_STORAGE_INTERVAL and interval not in STORAGE_TO_API_INTERVAL:
        return interval
    normalized = STORAGE_TO_API_INTERVAL.get(interval)
    if normalized is None:
        raise ValueError(f'Unsupported interval: {interval}')
    return normalized


def get_interval_bucket_ms(interval: str) -> int:
    normalized = normalize_interval_for_storage(interval)
    return INTERVAL_BUCKET_MS[normalized]


def build_candle_bucket_key(
    pool_application: str,
    pool_id: int,
    token_reversed: bool,
    interval: str,
    created_at_ms: int,
) -> CandleBucketKey:
    normalized_interval = normalize_interval_for_storage(interval)
    bucket_ms = get_interval_bucket_ms(normalized_interval)
    bucket_start_ms = created_at_ms // bucket_ms * bucket_ms

    return CandleBucketKey(
        pool_application=pool_application,
        pool_id=pool_id,
        token_reversed=token_reversed,
        interval=normalized_interval,
        bucket_start_ms=bucket_start_ms,
    )


def apply_candle_update(
    existing: CandleState | None,
    update: CandleUpdate,
) -> CandleState:
    def trade_order(created_at_ms: int, transaction_id: int):
        return (created_at_ms, transaction_id)

    if existing is None:
        return CandleState(
            open=update.price,
            high=update.price,
            low=update.price,
            close=update.price,
            base_volume=round(update.base_volume, 12),
            quote_volume=round(update.quote_volume, 12),
            trade_count=1,
            first_trade_id=update.transaction_id,
            last_trade_id=update.transaction_id,
            first_trade_at_ms=update.created_at_ms,
            last_trade_at_ms=update.created_at_ms,
        )

    update_order = trade_order(update.created_at_ms, update.transaction_id)
    first_order = trade_order(existing.first_trade_at_ms, existing.first_trade_id)
    last_order = trade_order(existing.last_trade_at_ms, existing.last_trade_id)

    # Exact replay of a boundary trade must be idempotent.
    if update_order == first_order or update_order == last_order:
        return existing

    if update_order < first_order:
        open_price = update.price
        first_trade_id = update.transaction_id
        first_trade_at_ms = update.created_at_ms
    else:
        open_price = existing.open
        first_trade_id = existing.first_trade_id
        first_trade_at_ms = existing.first_trade_at_ms

    if update_order > last_order:
        close_price = update.price
        last_trade_id = update.transaction_id
        last_trade_at_ms = update.created_at_ms
    else:
        close_price = existing.close
        last_trade_id = existing.last_trade_id
        last_trade_at_ms = existing.last_trade_at_ms

    return CandleState(
        open=open_price,
        high=max(existing.high, update.price),
        low=min(existing.low, update.price),
        close=close_price,
        base_volume=round(existing.base_volume + update.base_volume, 12),
        quote_volume=round(existing.quote_volume + update.quote_volume, 12),
        trade_count=existing.trade_count + 1,
        first_trade_id=first_trade_id,
        last_trade_id=last_trade_id,
        first_trade_at_ms=first_trade_at_ms,
        last_trade_at_ms=last_trade_at_ms,
    )
