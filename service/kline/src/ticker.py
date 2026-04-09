import asyncio
from swap import Pool, Transaction
from candle_schema import INTERVAL_BUCKET_MS, build_candle_bucket_key
from db import build_candle_point_payload


class Ticker:
    def __init__(self, manager, swap, db, now_ms=None):
        self.interval = 10 # seconds
        self.manager = manager
        self.swap = swap
        self.db = db
        self._running = True
        self._now_ms = now_ms if now_ms is not None else lambda: int(__import__('time').time() * 1000)
        self.last_emitted_bucket_starts = {}

    async def get_pools(self) -> list[Pool]:
        return await self.swap.get_pools()

    async def get_pool_transactions(self, pool: Pool, start_id: int = None) -> list[Transaction]:
        return await self.swap.get_pool_transactions(pool, start_id)

    async def persist_pools(self, pools: list[Pool]):
        await asyncio.to_thread(self.db.new_pools, pools)

    async def persist_transactions(self, pool_id: int, transactions: list[Transaction]):
        return await asyncio.to_thread(self.db.new_transactions, pool_id, transactions)

    async def build_incremental_kline_payload_async(self, pool: Pool, transactions):
        return await asyncio.to_thread(self.build_incremental_kline_payload, pool, transactions)

    def transaction_watermark(self, transaction):
        return (
            int(transaction['created_at']),
            int(transaction['transaction_id']),
            1 if bool(transaction['token_reversed']) else 0,
        )

    def resolve_transaction_start_id(self, pool: Pool, last_timestamps):
        if pool.pool_id in last_timestamps:
            return int(last_timestamps[pool.pool_id][1])

        latest_transaction = getattr(pool, 'latest_transaction', None)
        if latest_transaction is None:
            return None

        latest_transaction_id = getattr(latest_transaction, 'transaction_id', None)
        if latest_transaction_id is None:
            return None

        # Use the latest known transaction id as the lower bound so the
        # upstream query can return the freshest edge instead of an older default window.
        return max(int(latest_transaction_id) - 1, 0)

    def build_incremental_kline_payload(self, pool: Pool, transactions):
        payload = {}
        seen = set()

        for transaction in transactions:
            if transaction['transaction_type'] not in ['BuyToken0', 'SellToken0']:
                continue

            token_reversed = bool(transaction['token_reversed'])
            token_0 = pool.token_1 if token_reversed else pool.token_0
            token_1 = pool.token_0 if token_reversed else (pool.token_1 if pool.token_1 is not None else 'TLINERA')

            for interval, bucket_ms in INTERVAL_BUCKET_MS.items():
                bucket_key = build_candle_bucket_key(
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
                points = self.db.get_kline(
                    token_0=token_0,
                    token_1=token_1,
                    start_at=range_start,
                    end_at=bucket_key.bucket_start_ms,
                    interval=interval,
                )[2]
                if len(points) == 0:
                    continue

                seen.add(dedupe_key)
                interval_points = payload.get(interval, [])
                interval_points.append({
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

    def build_rollover_kline_payload(self, pool: Pool):
        payload = {}
        now_ms = self._now_ms()

        for token_reversed in [False, True]:
            token_0 = pool.token_1 if token_reversed else pool.token_0
            token_1 = pool.token_0 if token_reversed else (pool.token_1 if pool.token_1 is not None else 'TLINERA')

            for interval, bucket_ms in INTERVAL_BUCKET_MS.items():
                stream_key = (token_0, token_1, interval)
                last_emitted_bucket_start = self.last_emitted_bucket_starts.get(stream_key)
                if last_emitted_bucket_start is None:
                    continue

                current_bucket_start = build_candle_bucket_key(
                    pool_id=pool.pool_id,
                    token_reversed=token_reversed,
                    interval=interval,
                    created_at_ms=now_ms,
                ).bucket_start_ms
                if current_bucket_start <= last_emitted_bucket_start:
                    continue

                range_start = last_emitted_bucket_start + bucket_ms
                points = self.db.get_kline(
                    token_0=token_0,
                    token_1=token_1,
                    start_at=range_start,
                    end_at=current_bucket_start,
                    interval=interval,
                )[2]
                if len(points) == 0:
                    continue

                interval_points = payload.get(interval, [])
                interval_points.append({
                    'token_0': token_0,
                    'token_1': token_1,
                    'interval': interval,
                    'start_at': range_start,
                    'end_at': current_bucket_start + bucket_ms - 1,
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
            start_id = self.resolve_transaction_start_id(pool, last_timestamps)
            transactions = await self.get_pool_transactions(pool, start_id)
            __transactions = await self.persist_transactions(pool.pool_id, transactions)

            last_watermark = last_timestamps[pool.pool_id] if pool.pool_id in last_timestamps else (0, 0, -1)
            live_transactions = list(filter(
                lambda transaction: self.transaction_watermark(transaction) > last_watermark,
                __transactions,
            ))

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
            last_timestamps[pool.pool_id] = max(
                [self.transaction_watermark(transaction) for transaction in __transactions] + [last_watermark]
            )

        await self.manager.notify('kline', kline_payload)
        await self.manager.notify('transactions', _transactions)

    async def run(self):
        last_timestamps = {}

        while self._running:
            await self.run_iteration(last_timestamps)
            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False

    def running(self):
        return self._running
