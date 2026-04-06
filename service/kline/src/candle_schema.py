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
    pool_id: int
    token_reversed: bool
    interval: str
    bucket_start_ms: int


@dataclass(frozen=True)
class CandleUpdate:
    transaction_id: int
    created_at_ms: int
    price: float
    volume: float


@dataclass(frozen=True)
class CandleState:
    open: float
    high: float
    low: float
    close: float
    volume: float
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
    pool_id: int,
    token_reversed: bool,
    interval: str,
    created_at_ms: int,
) -> CandleBucketKey:
    bucket_ms = get_interval_bucket_ms(interval)
    bucket_start_ms = created_at_ms // bucket_ms * bucket_ms

    return CandleBucketKey(
        pool_id=pool_id,
        token_reversed=token_reversed,
        interval=interval,
        bucket_start_ms=bucket_start_ms,
    )


def apply_candle_update(
    existing: CandleState | None,
    update: CandleUpdate,
) -> CandleState:
    if existing is None:
        return CandleState(
            open=update.price,
            high=update.price,
            low=update.price,
            close=update.price,
            volume=round(update.volume, 12),
            trade_count=1,
            first_trade_id=update.transaction_id,
            last_trade_id=update.transaction_id,
            first_trade_at_ms=update.created_at_ms,
            last_trade_at_ms=update.created_at_ms,
        )

    if update.transaction_id <= existing.last_trade_id:
        return existing

    return CandleState(
        open=existing.open,
        high=max(existing.high, update.price),
        low=min(existing.low, update.price),
        close=update.price,
        volume=round(existing.volume + update.volume, 12),
        trade_count=existing.trade_count + 1,
        first_trade_id=existing.first_trade_id,
        last_trade_id=update.transaction_id,
        first_trade_at_ms=existing.first_trade_at_ms,
        last_trade_at_ms=update.created_at_ms,
    )
