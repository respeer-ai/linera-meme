import json
from decimal import Decimal

from candle_schema import CandleUpdate, apply_candle_update, build_candle_bucket_key, get_interval_bucket_ms
from storage.mysql.pool_identity_projection_repo import PoolIdentityProjectionRepository
from storage.mysql.settled_product_transaction_adapter import SettledProductTransactionAdapter
from transaction_family_codec import TransactionFamilyCodec


class SettledTradeProjectionRepository:
    def __init__(self, db, *, pool_identity_projection_repo=None, transaction_adapter=None, transaction_family_codec=None):
        self.db = db
        self.pool_identity_projection_repo = (
            pool_identity_projection_repo
            or PoolIdentityProjectionRepository(db)
        )
        self.transaction_adapter = transaction_adapter or SettledProductTransactionAdapter()
        self.transaction_family_codec = transaction_family_codec or TransactionFamilyCodec()

    def get_transactions(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
        start_at: int,
        end_at: int,
    ) -> list[dict] | None:
        rows = self._load_trade_rows(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
        )
        if rows is None:
            return None
        transactions = []
        for row in rows:
            transactions.extend(self._build_transaction_rows(row, duplicate_reverse=token_0 is None or token_1 is None))
        transactions.sort(key=lambda item: (int(item['created_at']), int(item['transaction_id'])))
        return transactions

    def get_transactions_information(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
    ) -> dict | None:
        rows = self._load_trade_rows(
            token_0=token_0,
            token_1=token_1,
            start_at=None,
            end_at=None,
        )
        if rows is None:
            return None
        count = 0
        timestamp_begin = None
        timestamp_end = None
        for row in rows:
            count += 2 if token_0 is None or token_1 is None else 1
            created_at = int(row['trade_time_ms'])
            timestamp_begin = created_at if timestamp_begin is None else max(timestamp_begin, created_at)
            timestamp_end = created_at if timestamp_end is None else min(timestamp_end, created_at)
        return {
            'count': count,
            'timestamp_begin': timestamp_begin,
            'timestamp_end': timestamp_end,
        }

    def get_pool_trade_history(
        self,
        *,
        pool_application: str,
        pool_id: int | None,
    ) -> list[dict] | None:
        rows = self._load_trade_rows(
            token_0=None,
            token_1=None,
            start_at=None,
            end_at=None,
            pool_application=pool_application,
            pool_id=pool_id,
        )
        if rows is None:
            return None
        history = []
        for row in rows:
            history.append(self._build_transaction_row(row, token_reversed=False))
        return history

    def get_candles(
        self,
        *,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> tuple[int | None, str | None, str, str, list[dict]] | None:
        try:
            resolved_pool_id, resolved_pool_application, resolved_token_0, resolved_token_1, token_reversed = (
                self.pool_identity_projection_repo.resolve_for_read(
                    token_0,
                    token_1,
                    pool_id=pool_id,
                    pool_application=pool_application,
                )
            )
        except Exception:
            return None
        rows = self._load_trade_rows(
            token_0=resolved_token_0,
            token_1=resolved_token_1,
            start_at=start_at,
            end_at=end_at,
            pool_application=resolved_pool_application,
            pool_id=resolved_pool_id,
        )
        if rows is None:
            return None
        previous_trade = self._load_previous_trade_row(
            pool_application=resolved_pool_application,
            before_ms=start_at,
        )
        points = self._build_candle_points(
            rows=rows,
            previous_trade=previous_trade,
            token_reversed=token_reversed,
            pool_application=resolved_pool_application,
            pool_id=resolved_pool_id,
            interval=interval,
            start_at=start_at,
            end_at=end_at,
        )
        return (
            resolved_pool_id,
            resolved_pool_application,
            resolved_token_0,
            resolved_token_1,
            points,
        )

    def get_candles_information(
        self,
        *,
        token_0: str,
        token_1: str,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ) -> dict | None:
        candles = self.get_candles(
            token_0=token_0,
            token_1=token_1,
            start_at=0,
            end_at=self.db.now_ms(),
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )
        if candles is None:
            return None
        points = candles[4]
        if not points:
            return {
                'count': 0,
                'timestamp_begin': None,
                'timestamp_end': None,
            }
        timestamps = [int(point['timestamp']) for point in points]
        return {
            'count': len(points),
            'timestamp_begin': max(timestamps),
            'timestamp_end': min(timestamps),
        }

    def _load_trade_rows(
        self,
        *,
        token_0: str | None,
        token_1: str | None,
        start_at: int | None,
        end_at: int | None,
        pool_application: str | None = None,
        pool_id: int | None = None,
    ) -> list[dict] | None:
        if not hasattr(self.db, 'ensure_fresh_read_connection'):
            return None
        if not hasattr(self.db, 'cursor_dict'):
            return None
        if not hasattr(self.db, 'pools_table'):
            return None
        self.db.ensure_fresh_read_connection()
        cursor = self.db.cursor_dict
        where_clauses = []
        params: list[object] = []
        if token_0 is not None and token_1 is not None:
            if pool_id is not None and pool_application is not None:
                where_clauses.append('p.pool_id = %s')
                params.append(int(pool_id))
                where_clauses.append('p.pool_application = %s')
                params.append(pool_application)
            else:
                try:
                    resolved_pool_id, resolved_pool_application, _resolved_token_0, _resolved_token_1, _token_reversed = (
                        self.pool_identity_projection_repo.resolve_for_tokens(token_0, token_1)
                    )
                except Exception:
                    return []
                where_clauses.append('p.pool_id = %s')
                params.append(int(resolved_pool_id))
                where_clauses.append('p.pool_application = %s')
                params.append(pool_application or resolved_pool_application)
        elif pool_application is not None:
            where_clauses.append('p.pool_application = %s')
            params.append(pool_application)
        if pool_id is not None:
            where_clauses.append('p.pool_id = %s')
            params.append(int(pool_id))
        if start_at is not None:
            where_clauses.append('st.trade_time_ms >= %s')
            params.append(int(start_at))
        if end_at is not None:
            where_clauses.append('st.trade_time_ms <= %s')
            params.append(int(end_at))
        where_sql = ''
        if where_clauses:
            where_sql = 'WHERE ' + ' AND '.join(where_clauses)
        try:
            cursor.execute(
                f'''
                SELECT
                    p.pool_id,
                    p.pool_application,
                    p.token_0,
                    p.token_1,
                    st.settled_trade_id,
                    st.transaction_id,
                    st.trade_time_ms,
                    st.side,
                    st.from_account,
                    st.amount_0_in,
                    st.amount_0_out,
                    st.amount_1_in,
                    st.amount_1_out,
                    st.amount_in,
                    st.amount_out,
                    st.event_payload_json
                FROM settled_trades st
                JOIN {self.db.pools_table} p
                  ON p.pool_application = CONCAT(st.pool_chain_id, ':', st.pool_application_id)
                {where_sql}
                ORDER BY st.trade_time_ms ASC, st.transaction_id ASC, st.settled_trade_id ASC
                ''',
                tuple(params),
            )
            return list(cursor.fetchall() or [])
        except Exception:
            return None

    def _build_transaction_rows(self, row: dict, *, duplicate_reverse: bool) -> list[dict]:
        forward = self._build_transaction_row(row, token_reversed=False)
        if not duplicate_reverse:
            return [forward]
        reverse = self._build_transaction_row(row, token_reversed=True)
        return [forward, reverse]

    def _build_transaction_row(self, row: dict, *, token_reversed: bool) -> dict:
        base_row = self.transaction_adapter.build_trade_history_row(row)
        base_volume, quote_volume, price = self._trade_metrics(
            row=row,
            token_reversed=token_reversed,
        )
        return {
            'pool_application': row['pool_application'],
            'pool_id': int(row['pool_id']),
            **base_row,
            'price': float(price),
            'volume': float(base_volume),
            'quote_volume': float(quote_volume),
            'direction': self._direction(str(base_row['transaction_type']), token_reversed=token_reversed),
            'token_reversed': bool(token_reversed),
        }

    def _build_candle_points(
        self,
        *,
        rows: list[dict],
        previous_trade: dict | None,
        token_reversed: bool,
        pool_application: str,
        pool_id: int,
        interval: str,
        start_at: int,
        end_at: int,
    ) -> list[dict]:
        bucket_states = {}
        for row in rows:
            base_volume, quote_volume, price = self._trade_metrics(
                row=row,
                token_reversed=token_reversed,
            )
            bucket_key = build_candle_bucket_key(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                created_at_ms=int(row['trade_time_ms']),
            )
            update = CandleUpdate(
                transaction_id=int(row['transaction_id']),
                created_at_ms=int(row['trade_time_ms']),
                price=float(price),
                base_volume=float(base_volume),
                quote_volume=float(quote_volume),
            )
            bucket_states[bucket_key.bucket_start_ms] = apply_candle_update(
                bucket_states.get(bucket_key.bucket_start_ms),
                update,
            )
        interval_ms = get_interval_bucket_ms(interval)
        start_bucket_ms = start_at // interval_ms * interval_ms
        end_bucket_ms = end_at // interval_ms * interval_ms
        previous_close = self._load_previous_close(
            previous_trade=previous_trade,
            token_reversed=token_reversed,
        )
        if not bucket_states and previous_close is None:
            return []
        points = []
        last_close = previous_close
        now_ms = self.db.now_ms()
        bucket_ms = start_bucket_ms
        while bucket_ms <= end_bucket_ms:
            state = bucket_states.get(bucket_ms)
            if state is not None:
                points.append(self._build_candle_point(interval=interval, bucket_start_ms=bucket_ms, state=state, now_ms=now_ms))
                last_close = state.close
            elif last_close is not None and now_ms > bucket_ms + interval_ms - 1:
                points.append(self._build_empty_candle_point(interval=interval, bucket_start_ms=bucket_ms, close_price=last_close, now_ms=now_ms))
            bucket_ms += interval_ms
        return points

    def _load_previous_close(
        self,
        *,
        previous_trade: dict | None,
        token_reversed: bool,
    ) -> float | None:
        if previous_trade is None:
            return None
        _base_volume, _quote_volume, price = self._trade_metrics(
            row=previous_trade,
            token_reversed=token_reversed,
        )
        return float(price)

    def _load_previous_trade_row(
        self,
        *,
        pool_application: str,
        before_ms: int,
    ) -> dict | None:
        self.db.ensure_fresh_read_connection()
        cursor = self.db.cursor_dict
        try:
            cursor.execute(
                f'''
                SELECT
                    p.pool_id,
                    p.pool_application,
                    p.token_0,
                    p.token_1,
                    st.settled_trade_id,
                    st.transaction_id,
                    st.trade_time_ms,
                    st.side,
                    st.from_account,
                    st.amount_0_in,
                    st.amount_0_out,
                    st.amount_1_in,
                    st.amount_1_out,
                    st.amount_in,
                    st.amount_out,
                    st.event_payload_json
                FROM settled_trades st
                JOIN {self.db.pools_table} p
                  ON p.pool_application = CONCAT(st.pool_chain_id, ':', st.pool_application_id)
                WHERE p.pool_application = %s
                  AND st.trade_time_ms < %s
                ORDER BY st.trade_time_ms DESC, st.transaction_id DESC, st.settled_trade_id DESC
                LIMIT 1
                ''',
                (pool_application, int(before_ms)),
            )
            rows = cursor.fetchall() or []
            if not rows:
                return None
            return rows[0]
        except Exception:
            return None

    def _trade_metrics(self, *, row: dict, token_reversed: bool) -> tuple[Decimal, Decimal, Decimal]:
        side = str(row['side'])
        amount_in = Decimal(str(row['amount_in']))
        amount_out = Decimal(str(row['amount_out']))
        if token_reversed:
            base_volume = amount_in if side == 'buy_token_0' else amount_out
            quote_volume = amount_out if side == 'buy_token_0' else amount_in
        else:
            base_volume = amount_out if side == 'buy_token_0' else amount_in
            quote_volume = amount_in if side == 'buy_token_0' else amount_out
        if base_volume == 0:
            price = Decimal('0')
        else:
            price = quote_volume / base_volume
        return base_volume, quote_volume, price

    def _direction(self, transaction_type: str, *, token_reversed: bool) -> str:
        return self.transaction_family_codec.trade_direction(
            transaction_type,
            token_reversed=token_reversed,
        )

    def _string_or_none(self, value: object) -> str | None:
        if value is None:
            return None
        return str(value)

    def _build_candle_point(self, *, interval: str, bucket_start_ms: int, state, now_ms: int) -> dict:
        bucket_ms = get_interval_bucket_ms(interval)
        return {
            'timestamp': bucket_start_ms,
            'bucket_start_ms': bucket_start_ms,
            'bucket_end_ms': bucket_start_ms + bucket_ms - 1,
            'is_final': now_ms > bucket_start_ms + bucket_ms - 1,
            'open': float(state.open),
            'high': float(state.high),
            'low': float(state.low),
            'close': float(state.close),
            'base_volume': float(state.base_volume),
            'quote_volume': float(state.quote_volume),
        }

    def _build_empty_candle_point(self, *, interval: str, bucket_start_ms: int, close_price: float, now_ms: int) -> dict:
        bucket_ms = get_interval_bucket_ms(interval)
        return {
            'timestamp': bucket_start_ms,
            'bucket_start_ms': bucket_start_ms,
            'bucket_end_ms': bucket_start_ms + bucket_ms - 1,
            'is_final': now_ms > bucket_start_ms + bucket_ms - 1,
            'open': float(close_price),
            'high': float(close_price),
            'low': float(close_price),
            'close': float(close_price),
            'base_volume': 0.0,
            'quote_volume': 0.0,
        }
