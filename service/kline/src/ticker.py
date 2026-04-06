import asyncio
from swap import Pool, Transaction
from candle_schema import INTERVAL_BUCKET_MS, build_candle_bucket_key


class Ticker:
    def __init__(self, manager, swap, db):
        self.interval = 10 # seconds
        self.manager = manager
        self.swap = swap
        self.db = db
        self._running = True

    async def get_pools(self) -> list[Pool]:
        return await self.swap.get_pools()

    async def get_pool_transactions(self, pool: Pool) -> list[Transaction]:
        return await self.swap.get_pool_transactions(pool)

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

                point = self.db.get_candle_point(
                    pool_id=pool.pool_id,
                    token_reversed=token_reversed,
                    interval=interval,
                    bucket_start_ms=bucket_key.bucket_start_ms,
                )
                if point is None:
                    continue

                seen.add(dedupe_key)
                interval_points = payload.get(interval, [])
                interval_points.append({
                    'token_0': token_0,
                    'token_1': token_1,
                    'interval': interval,
                    'start_at': bucket_key.bucket_start_ms,
                    'end_at': bucket_key.bucket_start_ms + bucket_ms - 1,
                    'points': [point],
                })
                payload[interval] = interval_points

        return payload

    async def run(self):
        lastTimestamps = {}

        while self._running:
            pools = await self.get_pools()
            self.db.new_pools(pools)

            _transactions = []
            kline_payload = {}

            for pool in pools:
                transactions = await self.get_pool_transactions(pool)
                __transactions = self.db.new_transactions(pool.pool_id, transactions)

                lastTimestamp = lastTimestamps[pool.pool_id] if pool.pool_id in lastTimestamps else 0
                live_transactions = list(filter(lambda transaction: transaction['created_at'] > lastTimestamp, __transactions))

                _transactions.append({
                    'token_0': pool.token_0,
                    'token_1': pool.token_1 if pool.token_1 is not None else 'TLINERA',
                    'transactions': live_transactions,
                })
                incremental_payload = self.build_incremental_kline_payload(pool, live_transactions)
                for interval, interval_points in incremental_payload.items():
                    existing = kline_payload.get(interval, [])
                    existing.extend(interval_points)
                    kline_payload[interval] = existing
                lastTimestamps[pool.pool_id] = max([transaction['created_at'] for transaction in __transactions] + [lastTimestamp])

            await self.manager.notify('kline', kline_payload)
            await self.manager.notify('transactions', _transactions)

            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False

    def running(self):
        return self._running
