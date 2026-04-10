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


def get_interval_bucket_ms(interval: str) -> int:
    if interval not in INTERVAL_BUCKET_MS:
        raise ValueError(f'Unsupported interval: {interval}')
    return INTERVAL_BUCKET_MS[interval]


def build_candle_bucket_key(
    pool_application: str,
    pool_id: int,
    token_reversed: bool,
    interval: str,
    created_at_ms: int,
) -> CandleBucketKey:
    bucket_ms = get_interval_bucket_ms(interval)
    bucket_start_ms = created_at_ms // bucket_ms * bucket_ms

    return CandleBucketKey(
        pool_application=pool_application,
        pool_id=pool_id,
        token_reversed=token_reversed,
        interval=interval,
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
