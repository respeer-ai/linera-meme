import asyncio

from candle_schema import INTERVAL_BUCKET_MS, build_candle_bucket_key


class Ticker:
    def __init__(
        self,
        manager,
        swap,
        pool_catalog_writer,
        candle_reader,
        transaction_history_repository,
        transaction_watermarks_repository,
        now_ms=None,
    ):
        self.interval = 10
        self.manager = manager
        self.swap = swap
        self.pool_catalog_writer = pool_catalog_writer
        self.candle_reader = candle_reader
        self.transaction_history_repository = transaction_history_repository
        self.transaction_watermarks_repository = transaction_watermarks_repository
        self._running = True
        self._now_ms = now_ms if now_ms is not None else lambda: int(__import__('time').time() * 1000)
        self.last_emitted_bucket_starts = {}

    def load_candle_points(
        self,
        *,
        token_0: str,
        token_1: str,
        start_at: int,
        end_at: int,
        interval: str,
        pool_id: int,
        pool_application: str,
    ) -> list[dict]:
        return self.candle_reader.get_points(
            token_0=token_0,
            token_1=token_1,
            start_at=start_at,
            end_at=end_at,
            interval=interval,
            pool_id=pool_id,
            pool_application=pool_application,
        )['points']

    async def get_pools(self):
        return await self.swap.get_pools()

    async def persist_pools(self, pools):
        await asyncio.to_thread(self.pool_catalog_writer.upsert_pools, pools)

    async def build_incremental_kline_payload_async(self, pool, transactions):
        return await asyncio.to_thread(self.build_incremental_kline_payload, pool, transactions)

    def log_event(self, event: str, **fields):
        parts = [f'[ticker] event={event}']
        for key in sorted(fields.keys()):
            parts.append(f'{key}={fields[key]}')
        print(' '.join(parts))

    def transaction_id_value(self, transaction):
        return int(transaction['transaction_id'])

    def transaction_watermark(self, transaction):
        return (
            int(transaction['created_at']),
            int(transaction['transaction_id']),
            1 if bool(transaction['token_reversed']) else 0,
        )

    def pool_identity(self, pool):
        return (
            pool.pool_id,
            pool.pool_application.chain_id,
            pool.pool_application.owner,
        )

    def pool_application(self, pool):
        return f'{pool.pool_application.chain_id}:{pool.pool_application.owner}'

    def resolve_transaction_start_id(self, pool, last_timestamps):
        pool_identity = self.pool_identity(pool)
        if pool_identity in last_timestamps:
            return int(last_timestamps[pool_identity][1])
        return None

    def load_pool_transactions(self, pool, start_id=None):
        history = self.transaction_history_repository.get_pool_transaction_history(
            pool_application=self.pool_application(pool),
            pool_id=pool.pool_id,
        )
        if start_id is None:
            return list(history)
        lower_bound = int(start_id)
        return [
            transaction
            for transaction in history
            if int(transaction.get('transaction_id') or 0) >= lower_bound
        ]

    def build_incremental_kline_payload(self, pool, transactions):
        payload = {}
        seen = set()
        pool_application = self.pool_application(pool)

        for transaction in transactions:
            if transaction['transaction_type'] not in ['BuyToken0', 'SellToken0']:
                continue

            token_reversed = bool(transaction['token_reversed'])
            token_0 = pool.token_1 if token_reversed else pool.token_0
            token_1 = pool.token_0 if token_reversed else (pool.token_1 if pool.token_1 is not None else 'TLINERA')

            for interval, bucket_ms in INTERVAL_BUCKET_MS.items():
                bucket_key = build_candle_bucket_key(
                    pool_application=f'{pool.pool_application.chain_id}:{pool.pool_application.owner}',
                    pool_id=pool.pool_id,
                    token_reversed=token_reversed,
                    interval=interval,
                    created_at_ms=int(transaction['created_at']),
                )
                dedupe_key = (token_0, token_1, interval, bucket_key.bucket_start_ms)
                if dedupe_key in seen:
                    continue

                stream_key = (token_0, token_1, interval)
                last_emitted_bucket_start = self.last_emitted_bucket_starts.get(stream_key)
                range_start = (
                    bucket_key.bucket_start_ms
                    if last_emitted_bucket_start is None or bucket_key.bucket_start_ms <= last_emitted_bucket_start
                    else last_emitted_bucket_start + bucket_ms
                )
                points = self.load_candle_points(
                    token_0=token_0,
                    token_1=token_1,
                    start_at=range_start,
                    end_at=bucket_key.bucket_start_ms,
                    interval=interval,
                    pool_id=pool.pool_id,
                    pool_application=pool_application,
                )
                if len(points) == 0:
                    self.log_event(
                        'incremental_points_empty',
                        bucket_start_ms=bucket_key.bucket_start_ms,
                        interval=interval,
                        pool_id=pool.pool_id,
                        range_start=range_start,
                        token_0=token_0,
                        token_1=token_1,
                        token_reversed=token_reversed,
                        transaction_id=transaction['transaction_id'],
                    )
                    continue

                seen.add(dedupe_key)
                last_point = points[-1]
                self.log_event(
                    'incremental_points_ready',
                    base_volume=last_point['base_volume'],
                    bucket_start_ms=last_point['bucket_start_ms'],
                    close=last_point['close'],
                    interval=interval,
                    point_count=len(points),
                    pool_id=pool.pool_id,
                    quote_volume=last_point['quote_volume'],
                    range_start=range_start,
                    token_0=token_0,
                    token_1=token_1,
                    token_reversed=token_reversed,
                    transaction_id=transaction['transaction_id'],
                )
                interval_points = payload.get(interval, [])
                interval_points.append({
                    'pool_id': pool.pool_id,
                    'pool_application': pool_application,
                    'token_0': token_0,
                    'token_1': token_1,
                    'interval': interval,
                    'start_at': range_start,
                    'end_at': bucket_key.bucket_start_ms + bucket_ms - 1,
                    'points': points,
                })
                payload[interval] = interval_points
                self.last_emitted_bucket_starts[stream_key] = max(
                    int(point['bucket_start_ms'])
                    for point in points
                )

        return payload

    def build_rollover_kline_payload(self, pool):
        payload = {}
        now_ms = self._now_ms()
        pool_application = self.pool_application(pool)

        for token_reversed in [False, True]:
            token_0 = pool.token_1 if token_reversed else pool.token_0
            token_1 = pool.token_0 if token_reversed else (pool.token_1 if pool.token_1 is not None else 'TLINERA')

            for interval, bucket_ms in INTERVAL_BUCKET_MS.items():
                stream_key = (token_0, token_1, interval)
                last_emitted_bucket_start = self.last_emitted_bucket_starts.get(stream_key)
                if last_emitted_bucket_start is None:
                    continue

                current_bucket_start = build_candle_bucket_key(
                    pool_application=f'{pool.pool_application.chain_id}:{pool.pool_application.owner}',
                    pool_id=pool.pool_id,
                    token_reversed=token_reversed,
                    interval=interval,
                    created_at_ms=now_ms,
                ).bucket_start_ms
                last_finalized_bucket_start = current_bucket_start - bucket_ms
                if last_finalized_bucket_start <= last_emitted_bucket_start:
                    continue

                range_start = last_emitted_bucket_start + bucket_ms
                range_end = last_finalized_bucket_start
                points = self.load_candle_points(
                    token_0=token_0,
                    token_1=token_1,
                    start_at=range_start,
                    end_at=range_end,
                    interval=interval,
                    pool_id=pool.pool_id,
                    pool_application=pool_application,
                )
                if len(points) == 0:
                    continue

                interval_points = payload.get(interval, [])
                interval_points.append({
                    'pool_id': pool.pool_id,
                    'pool_application': pool_application,
                    'token_0': token_0,
                    'token_1': token_1,
                    'interval': interval,
                    'start_at': range_start,
                    'end_at': range_end + bucket_ms - 1,
                    'points': points,
                })
                payload[interval] = interval_points
                self.last_emitted_bucket_starts[stream_key] = max(
                    int(point['bucket_start_ms'])
                    for point in points
                )

        return payload

    async def run_iteration(self, last_timestamps):
        pools = await self.get_pools()
        await self.persist_pools(pools)

        _transactions = []
        kline_payload = {}

        for pool in pools:
            pool_identity = self.pool_identity(pool)
            start_id = self.resolve_transaction_start_id(pool, last_timestamps)
            transactions = await asyncio.to_thread(self.load_pool_transactions, pool, start_id)
            fetched_ids = ','.join(str(self.transaction_id_value(transaction)) for transaction in transactions[:8])
            self.log_event(
                'pool_transactions_loaded',
                fetched_count=len(transactions),
                fetched_ids=fetched_ids if fetched_ids else 'none',
                last_known_watermark=last_timestamps.get(pool_identity, 'none'),
                pool_id=pool.pool_id,
                requested_start_id=start_id if start_id is not None else 'none',
            )

            last_watermark = last_timestamps[pool_identity] if pool_identity in last_timestamps else (0, 0, -1)
            live_transactions = list(filter(
                lambda transaction: self.transaction_watermark(transaction) > last_watermark,
                transactions,
            ))
            live_ids = ','.join(str(transaction['transaction_id']) for transaction in live_transactions[:8])
            self.log_event(
                'pool_transactions_live',
                last_watermark=last_watermark,
                live_count=len(live_transactions),
                live_ids=live_ids if live_ids else 'none',
                pool_id=pool.pool_id,
            )

            _transactions.append({
                'token_0': pool.token_0,
                'token_1': pool.token_1 if pool.token_1 is not None else 'TLINERA',
                'transactions': live_transactions,
            })
            incremental_payload = await self.build_incremental_kline_payload_async(pool, live_transactions)
            for interval, interval_points in incremental_payload.items():
                existing = kline_payload.get(interval, [])
                existing.extend(interval_points)
                kline_payload[interval] = existing
            rollover_payload = await asyncio.to_thread(self.build_rollover_kline_payload, pool)
            for interval, interval_points in rollover_payload.items():
                existing = kline_payload.get(interval, [])
                existing.extend(interval_points)
                kline_payload[interval] = existing
            if len(live_transactions) > 0:
                last_timestamps[pool_identity] = max(
                    [self.transaction_watermark(transaction) for transaction in live_transactions] + [last_watermark]
                )
            elif pool_identity not in last_timestamps and len(transactions) > 0:
                last_timestamps[pool_identity] = max(
                    self.transaction_watermark(transaction)
                    for transaction in transactions
                )

        await self.manager.notify('kline', kline_payload)
        await self.manager.notify('transactions', _transactions)

    async def run(self):
        last_timestamps = await asyncio.to_thread(
            self.transaction_watermarks_repository.get_latest_transaction_watermarks
        )

        while self._running:
            await self.run_iteration(last_timestamps)
            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False

    def running(self):
        return self._running
