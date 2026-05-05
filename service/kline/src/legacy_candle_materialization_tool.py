import time

from candle_schema import INTERVAL_BUCKET_MS, build_candle_bucket_key, get_interval_bucket_ms


class LegacyCandleMaterializationTool:
    def __init__(self, db):
        self.db = db

    def rebuild_pair_candles(
        self,
        *,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        intervals=None,
    ):
        pool_id, pool_application, resolved_token_0, resolved_token_1, token_reversed = (
            self.db.get_pool_identity(token_0, token_1)
        )
        selected_intervals = list(intervals) if intervals is not None else list(INTERVAL_BUCKET_MS.keys())
        results = {}
        for interval in selected_intervals:
            results[f'{interval}:forward'] = self.db.rebuild_candles_from_transactions(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=interval,
                start_at=start_at,
                end_at=end_at,
            )
            results[f'{interval}:reverse'] = self.db.rebuild_candles_from_transactions(
                pool_application=pool_application,
                pool_id=pool_id,
                token_reversed=not token_reversed,
                interval=interval,
                start_at=start_at,
                end_at=end_at,
            )
        return results

    def get_kline_information(
        self,
        *,
        token_0: str,
        token_1: str,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ):
        self.db.ensure_fresh_read_connection()
        resolved_pool_id, resolved_pool_application, _resolved_token_0, _resolved_token_1, token_reversed = (
            self.db.resolve_pool_identity_for_read(
                token_0,
                token_1,
                pool_id=pool_id,
                pool_application=pool_application,
            )
        )
        query = f'''
            SELECT
                COUNT(*) AS count,
                MAX(created_at) AS timestamp_begin,
                MIN(created_at) AS timestamp_end
            FROM {self.db.transactions_table}
            WHERE pool_application = "{resolved_pool_application}"
            AND pool_id = {resolved_pool_id}
            AND token_reversed = {token_reversed}
            AND transaction_type != 'AddLiquidity'
            AND transaction_type != 'RemoveLiquidity';
        '''
        self.db.cursor_dict.execute(query)
        return self.db.cursor_dict.fetchone()

    def get_kline(
        self,
        *,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        interval: str,
        pool_id: int | None = None,
        pool_application: str | None = None,
    ):
        self.db.ensure_fresh_read_connection()
        request_started_at = time.perf_counter()
        resolved_pool_id, resolved_pool_application, resolved_token_0, resolved_token_1, token_reversed = (
            self.db.resolve_pool_identity_for_read(
                token_0,
                token_1,
                pool_id=pool_id,
                pool_application=pool_application,
            )
        )
        resolved_interval = interval if interval is not None else '1min'
        self.db.log_kline_event(
            event='request_start',
            end_at=end_at,
            interval=resolved_interval,
            pool_id=resolved_pool_id,
            start_at=start_at,
            token_reversed=token_reversed,
        )
        points = self.db.get_kline_from_candles(
            pool_application=resolved_pool_application,
            pool_id=resolved_pool_id,
            token_reversed=token_reversed,
            token_0=resolved_token_0,
            token_1=resolved_token_1,
            start_at=start_at,
            end_at=end_at,
            interval=resolved_interval,
        )
        self.db.log_kline_event(
            event='candles_result',
            interval=resolved_interval,
            point_count=len(points),
            pool_id=resolved_pool_id,
            token_reversed=token_reversed,
        )
        self.db.log_kline_event(
            event='request_complete',
            duration_ms=int((time.perf_counter() - request_started_at) * 1000),
            interval=resolved_interval,
            point_count=len(points),
            pool_id=resolved_pool_id,
            source='candles',
            token_reversed=token_reversed,
        )
        return (
            resolved_pool_id,
            resolved_pool_application,
            resolved_token_0,
            resolved_token_1,
            points,
        )

    def get_kline_from_candles(
        self,
        *,
        pool_id: int,
        token_reversed: bool,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        interval: str,
        pool_application: str | None = None,
    ):
        resolved_pool_application = self.db.resolve_pool_application(pool_id, pool_application)
        resolved_interval = interval if interval is not None else '1min'
        query_start_at = build_candle_bucket_key(
            pool_application=resolved_pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=resolved_interval,
            created_at_ms=start_at,
        ).bucket_start_ms
        query_end_at = build_candle_bucket_key(
            pool_application=resolved_pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=resolved_interval,
            created_at_ms=end_at,
        ).bucket_start_ms
        query_started_at = time.perf_counter()
        self.db.cursor_dict.execute(
            f'''
                SELECT
                    bucket_start_ms,
                    open,
                    high,
                    low,
                    close,
                    volume,
                    quote_volume
                FROM {self.db.candles_table}
                WHERE pool_application = %s
                AND pool_id = %s
                AND token_reversed = %s
                AND interval_name = %s
                AND bucket_start_ms >= %s
                AND bucket_start_ms <= %s
                ORDER BY bucket_start_ms ASC
            ''',
            (resolved_pool_application, pool_id, token_reversed, resolved_interval, query_start_at, query_end_at),
        )
        rows = self.db.cursor_dict.fetchall()
        query_duration_ms = int((time.perf_counter() - query_started_at) * 1000)
        self.db.log_kline_event(
            event='candles_query',
            bucket_end_ms=query_end_at,
            bucket_start_ms=query_start_at,
            interval=resolved_interval,
            pool_id=pool_id,
            query_ms=query_duration_ms,
            row_count=len(rows),
            token_reversed=token_reversed,
        )
        if len(rows) == 0:
            previous_candle = self.db.load_previous_candle(
                pool_application=resolved_pool_application,
                pool_id=pool_id,
                token_reversed=token_reversed,
                interval=resolved_interval,
                before_bucket_start_ms=query_start_at,
            )
            if previous_candle is None:
                return []
            return self._build_continuous_candle_points(
                interval=resolved_interval,
                start_bucket_ms=query_start_at,
                end_bucket_ms=query_end_at,
                points=[],
                previous_close=previous_candle.close,
                now_ms=self.db.now_ms(),
            )

        if any(row.get('quote_volume') is None for row in rows):
            self.db.log_kline_event(
                event='candles_missing_quote_volume',
                interval=resolved_interval,
                pool_id=pool_id,
                row_count=len(rows),
                token_reversed=token_reversed,
            )
            return []

        now_ms = self.db.now_ms()
        points = []
        for row in rows:
            points.append({
                'timestamp': int(row['bucket_start_ms']),
                'bucket_start_ms': int(row['bucket_start_ms']),
                'bucket_end_ms': int(row['bucket_start_ms']) + get_interval_bucket_ms(resolved_interval) - 1,
                'is_final': now_ms > int(row['bucket_start_ms']) + get_interval_bucket_ms(resolved_interval) - 1,
                'open': float(row['open']),
                'high': float(row['high']),
                'low': float(row['low']),
                'close': float(row['close']),
                'base_volume': float(row['volume']),
                'quote_volume': float(row['quote_volume']),
            })

        previous_candle = self.db.load_previous_candle(
            pool_application=resolved_pool_application,
            pool_id=pool_id,
            token_reversed=token_reversed,
            interval=resolved_interval,
            before_bucket_start_ms=query_start_at,
        )
        previous_close = previous_candle.close if previous_candle is not None else None
        return self._build_continuous_candle_points(
            interval=resolved_interval,
            start_bucket_ms=query_start_at,
            end_bucket_ms=query_end_at,
            points=points,
            previous_close=previous_close,
            now_ms=now_ms,
        )

    def _build_continuous_candle_points(
        self,
        *,
        interval: str,
        start_bucket_ms: int,
        end_bucket_ms: int,
        points: list[dict],
        previous_close: float | None,
        now_ms: int,
    ):
        interval_ms = get_interval_bucket_ms(interval)
        points_by_bucket = {
            int(point['bucket_start_ms']): point
            for point in points
        }
        continuous_points = []
        last_close = previous_close

        bucket_start_ms = start_bucket_ms
        while bucket_start_ms <= end_bucket_ms:
            point = points_by_bucket.get(bucket_start_ms)
            bucket_end_ms = bucket_start_ms + interval_ms - 1
            if point is not None:
                continuous_points.append(point)
                last_close = float(point['close'])
            elif last_close is not None and now_ms > bucket_end_ms:
                continuous_points.append({
                    'timestamp': bucket_start_ms,
                    'bucket_start_ms': bucket_start_ms,
                    'bucket_end_ms': bucket_end_ms,
                    'is_final': True,
                    'open': float(last_close),
                    'high': float(last_close),
                    'low': float(last_close),
                    'close': float(last_close),
                    'base_volume': 0.0,
                    'quote_volume': 0.0,
                })
            bucket_start_ms += interval_ms

        return continuous_points
