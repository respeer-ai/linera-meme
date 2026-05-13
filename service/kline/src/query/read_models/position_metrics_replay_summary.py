from time_codec import TimeCodec


class PositionMetricsReplaySummary:
    def __init__(self, payload: dict | None):
        self.payload = payload or {}

    @classmethod
    def from_histories(
        cls,
        *,
        liquidity_history: list[dict] | None,
        pool_transaction_history: list[dict] | None,
    ):
        return cls(
            {
                'latest_position_transaction_id': cls._row_transaction_id(
                    cls._latest_row(liquidity_history)
                ),
                'latest_position_created_at': cls._row_time_ms(
                    cls._latest_row(liquidity_history)
                ),
                'latest_pool_transaction_id': cls._row_transaction_id(
                    cls._latest_row(pool_transaction_history)
                ),
                'latest_pool_trade_time_ms': cls._latest_created_at(
                    pool_transaction_history,
                    {'BuyToken0', 'SellToken0'},
                ),
                'latest_pool_liquidity_event_time_ms': cls._latest_created_at(
                    pool_transaction_history,
                    {'AddLiquidity', 'RemoveLiquidity'},
                ),
            }
        )

    def latest_position_transaction_id(self) -> int | None:
        return self.payload.get('latest_position_transaction_id')

    def latest_position_created_at(self) -> int | None:
        return self.payload.get('latest_position_created_at')

    def latest_pool_transaction_id(self) -> int | None:
        return self.payload.get('latest_pool_transaction_id')

    def latest_pool_trade_time_ms(self) -> int | None:
        return self.payload.get('latest_pool_trade_time_ms')

    def latest_pool_liquidity_event_time_ms(self) -> int | None:
        return self.payload.get('latest_pool_liquidity_event_time_ms')

    def as_dict(self) -> dict:
        return dict(self.payload)

    def shadow_latest_dict(self) -> dict:
        return {
            'latest_position_transaction_id': self.latest_position_transaction_id(),
            'latest_position_created_at': self.latest_position_created_at(),
            'latest_pool_transaction_id': self.latest_pool_transaction_id(),
            'latest_pool_trade_time_ms': self.latest_pool_trade_time_ms(),
            'latest_pool_liquidity_event_time_ms': self.latest_pool_liquidity_event_time_ms(),
        }

    @classmethod
    def _latest_row(cls, rows: list[dict] | None) -> dict | None:
        if not rows:
            return None
        return max(
            rows,
            key=lambda row: (
                cls._row_time_ms(row) or 0,
                cls._row_transaction_id(row) or 0,
                str(row.get('transaction_type') or ''),
            ),
        )

    @classmethod
    def _latest_created_at(
        cls,
        rows: list[dict] | None,
        allowed_types: set[str],
    ) -> int | None:
        timestamps = [
            cls._row_time_ms(row) or 0
            for row in (rows or [])
            if row.get('transaction_type') in allowed_types and cls._row_time_ms(row) is not None
        ]
        if not timestamps:
            return None
        return max(timestamps)

    @classmethod
    def _row_transaction_id(cls, row: dict | None) -> int | None:
        if row is None:
            return None
        value = row.get('transaction_id')
        if value in (None, ''):
            return None
        return int(value)

    @classmethod
    def _row_time_ms(cls, row: dict | None) -> int | None:
        if row is None:
            return None
        return TimeCodec().row_time_ms(row, 'created_at')
