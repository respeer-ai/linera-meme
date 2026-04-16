import asyncio
import os
from swap import Pool, Transaction
from candle_schema import INTERVAL_BUCKET_MS, build_candle_bucket_key
from db import build_candle_point_payload


class RecentPoolHistoryGapError(RuntimeError):
    def __init__(
        self,
        *,
        pool_id: int,
        pool_application: str,
        start_id: int,
        end_id: int,
        missing_ids: list[int],
    ):
        self.pool_id = int(pool_id)
        self.pool_application = pool_application
        self.start_id = int(start_id)
        self.end_id = int(end_id)
        self.missing_ids = list(missing_ids)
        preview = ','.join(str(transaction_id) for transaction_id in self.missing_ids[:8]) or 'none'
        super().__init__(
            f'Pool {self.pool_id} ({self.pool_application}) recent transaction history has internal gaps '
            f'between {self.start_id} and {self.end_id}; first missing ids: {preview}'
        )


class HistoricalPoolHistoryGapError(RuntimeError):
    def __init__(
        self,
        *,
        pool_id: int,
        pool_application: str,
        start_id: int,
        end_id: int,
        missing_ids: list[int],
    ):
        self.pool_id = int(pool_id)
        self.pool_application = pool_application
        self.start_id = int(start_id)
        self.end_id = int(end_id)
        self.missing_ids = list(missing_ids)
        preview = ','.join(str(transaction_id) for transaction_id in self.missing_ids[:8]) or 'none'
        super().__init__(
            f'Pool {self.pool_id} ({self.pool_application}) historical transaction history has internal gaps '
            f'between {self.start_id} and {self.end_id}; first missing ids: {preview}'
        )


class Ticker:
    def __init__(self, manager, swap, db, now_ms=None):
        self.interval = 10 # seconds
        self.manager = manager
        self.swap = swap
        self.db = db
        self._running = True
        self._now_ms = now_ms if now_ms is not None else lambda: int(__import__('time').time() * 1000)
        self.last_emitted_bucket_starts = {}
        self.recent_backfill_transaction_count = int(os.getenv('KLINE_RECENT_BACKFILL_TRANSACTION_COUNT', '5000'))
        self.initial_transaction_id = int(os.getenv('KLINE_INITIAL_TRANSACTION_ID', '1000'))
        self.backfilled_pools = set()
        self.audited_historical_pools = set()

    async def get_pools(self) -> list[Pool]:
        return await self.swap.get_pools()

    async def get_pool_transactions(self, pool: Pool, start_id: int = None) -> list[Transaction]:
        return await self.swap.get_pool_transactions(pool, start_id)

    async def persist_pools(self, pools: list[Pool]):
        await asyncio.to_thread(self.db.new_pools, pools)

    async def persist_transactions(self, pool: Pool, transactions: list[Transaction]):
        return await asyncio.to_thread(self.db.new_transactions, pool, transactions)

    async def build_incremental_kline_payload_async(self, pool: Pool, transactions):
        return await asyncio.to_thread(self.build_incremental_kline_payload, pool, transactions)

    def log_event(self, event: str, **fields):
        parts = [f'[ticker] event={event}']
        for key in sorted(fields.keys()):
            parts.append(f'{key}={fields[key]}')
        print(' '.join(parts))

    def transaction_id_value(self, transaction):
        if isinstance(transaction, dict):
            return transaction['transaction_id']
        return transaction.transaction_id

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

    def resolve_transaction_start_id(self, pool: Pool, last_timestamps):
        pool_identity = self.pool_identity(pool)
        if pool_identity in last_timestamps:
            return int(last_timestamps[pool_identity][1])
        return None

    def resolve_recent_backfill_start_id(self, pool: Pool):
        if self.recent_backfill_transaction_count <= 0:
            return None

        latest_transaction = getattr(pool, 'latest_transaction', None)
        if latest_transaction is None:
            return None

        latest_transaction_id = getattr(latest_transaction, 'transaction_id', None)
        if latest_transaction_id is None:
            return None

        return max(int(latest_transaction_id) - self.recent_backfill_transaction_count + 1, 0)

    def find_missing_transaction_ids(self, transaction_ids, start_id: int, end_id: int):
        if start_id > end_id:
            return []

        observed_ids = sorted({
            int(transaction_id)
            for transaction_id in transaction_ids
            if transaction_id is not None
        })
        observed_set = set(observed_ids)
        return [
            transaction_id
            for transaction_id in range(int(start_id), int(end_id) + 1)
            if transaction_id not in observed_set
        ]

    async def audit_recent_pool_history(self, pool: Pool):
        start_id = self.resolve_recent_backfill_start_id(pool)
        latest_transaction = getattr(pool, 'latest_transaction', None)
        latest_transaction_id = getattr(latest_transaction, 'transaction_id', None)
        if start_id is None or latest_transaction_id is None:
            return []

        pool_application = f'{pool.pool_application.chain_id}:{pool.pool_application.owner}'
        transaction_ids = await asyncio.to_thread(
            self.db.get_pool_transaction_ids,
            pool.pool_id,
            pool_application,
            start_id,
            int(latest_transaction_id),
        )
        missing_ids = self.find_missing_transaction_ids(
            transaction_ids,
            start_id,
            int(latest_transaction_id),
        )
        if missing_ids:
            preview = ','.join(str(transaction_id) for transaction_id in missing_ids[:8])
            self.log_event(
                'pool_transactions_recent_gap_detected',
                pool_application=pool_application,
                latest_transaction_id=int(latest_transaction_id),
                missing_count=len(missing_ids),
                missing_ids=preview if preview else 'none',
                pool_id=pool.pool_id,
                recent_window_end_id=int(latest_transaction_id),
                recent_window_start_id=start_id,
            )
            await asyncio.to_thread(
                self.db.record_diagnostic_event,
                source='ticker',
                event_type='recent_pool_history_gap',
                severity='warning',
                pool_application=pool_application,
                pool_id=pool.pool_id,
                details={
                    'start_id': start_id,
                    'end_id': int(latest_transaction_id),
                    'missing_count': len(missing_ids),
                    'missing_ids_sample': missing_ids[:8],
                },
            )
        return missing_ids

    async def audit_historical_pool_history(self, pool: Pool):
        pool_identity = self.pool_identity(pool)
        if pool_identity in self.audited_historical_pools:
            return []

        pool_application = f'{pool.pool_application.chain_id}:{pool.pool_application.owner}'
        bounds = await asyncio.to_thread(
            self.db.get_pool_transaction_id_bounds,
            pool.pool_id,
            pool_application,
        )
        if bounds is None:
            self.audited_historical_pools.add(pool_identity)
            return []

        start_id = max(int(bounds['min_transaction_id']), self.initial_transaction_id)
        end_id = int(bounds['max_transaction_id'])
        transaction_ids = await asyncio.to_thread(
            self.db.get_pool_transaction_ids,
            pool.pool_id,
            pool_application,
            start_id,
            end_id,
        )
        missing_ids = self.find_missing_transaction_ids(transaction_ids, start_id, end_id)
        if missing_ids:
            preview = ','.join(str(transaction_id) for transaction_id in missing_ids[:8])
            self.log_event(
                'pool_transactions_historical_gap_detected',
                pool_application=pool_application,
                missing_count=len(missing_ids),
                missing_ids=preview if preview else 'none',
                pool_id=pool.pool_id,
                history_end_id=end_id,
                history_start_id=start_id,
            )
            await asyncio.to_thread(
                self.db.record_diagnostic_event,
                source='ticker',
                event_type='historical_pool_history_gap',
                severity='warning',
                pool_application=pool_application,
                pool_id=pool.pool_id,
                details={
                    'start_id': start_id,
                    'end_id': end_id,
                    'missing_count': len(missing_ids),
                    'missing_ids_sample': missing_ids[:8],
                },
            )
        self.audited_historical_pools.add(pool_identity)
        return missing_ids

    def resolve_historical_repair_start_id(self, pool: Pool, bounds):
        latest_transaction = getattr(pool, 'latest_transaction', None)
        latest_transaction_id = getattr(latest_transaction, 'transaction_id', None)
        if latest_transaction_id is None:
            return None

        latest_transaction_id = int(latest_transaction_id)
        if latest_transaction_id < self.initial_transaction_id:
            return None

        if bounds is None:
            return self.initial_transaction_id

        if int(bounds['min_transaction_id']) <= self.initial_transaction_id:
            return None

        return self.initial_transaction_id

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
                points = self.db.get_kline(
                    token_0=token_0,
                    token_1=token_1,
                    start_at=range_start,
                    end_at=bucket_key.bucket_start_ms,
                    interval=interval,
                    pool_id=pool.pool_id,
                    pool_application=f'{pool.pool_application.chain_id}:{pool.pool_application.owner}',
                )[4]
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
                    'pool_application': f'{pool.pool_application.chain_id}:{pool.pool_application.owner}',
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
                points = self.db.get_kline(
                    token_0=token_0,
                    token_1=token_1,
                    start_at=range_start,
                    end_at=range_end,
                    interval=interval,
                    pool_id=pool.pool_id,
                    pool_application=f'{pool.pool_application.chain_id}:{pool.pool_application.owner}',
                )[4]
                if len(points) == 0:
                    continue

                interval_points = payload.get(interval, [])
                interval_points.append({
                    'pool_id': pool.pool_id,
                    'pool_application': f'{pool.pool_application.chain_id}:{pool.pool_application.owner}',
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

    async def backfill_recent_pool_history(self, pool: Pool, last_timestamps):
        pool_identity = self.pool_identity(pool)
        if pool_identity in self.backfilled_pools:
            return

        start_id = self.resolve_recent_backfill_start_id(pool)
        if start_id is None:
            self.backfilled_pools.add(pool_identity)
            return

        transactions = await self.get_pool_transactions(pool, start_id)
        pool_application = f'{pool.pool_application.chain_id}:{pool.pool_application.owner}'
        await asyncio.to_thread(
            self.db.record_diagnostic_event,
            source='ticker',
            event_type='recent_backfill_fetch',
            severity='info',
            pool_application=pool_application,
            pool_id=pool.pool_id,
            details={
                'start_id': start_id,
                'fetched_count': len(transactions),
                'fetched_ids_sample': [
                    int(self.transaction_id_value(transaction))
                    for transaction in transactions[:8]
                ],
            },
        )
        persisted_transactions = await self.persist_transactions(pool, transactions)
        if len(persisted_transactions) > 0:
            last_watermark = last_timestamps.get(pool_identity, (0, 0, -1))
            last_timestamps[pool_identity] = max(
                [self.transaction_watermark(transaction) for transaction in persisted_transactions] + [last_watermark]
            )

        self.backfilled_pools.add(pool_identity)

    async def repair_historical_pool_history(self, pool: Pool, last_timestamps):
        pool_application = f'{pool.pool_application.chain_id}:{pool.pool_application.owner}'
        bounds = await asyncio.to_thread(
            self.db.get_pool_transaction_id_bounds,
            pool.pool_id,
            pool_application,
        )
        repair_start_id = self.resolve_historical_repair_start_id(pool, bounds)
        if repair_start_id is None:
            return

        transactions = await self.get_pool_transactions(pool, repair_start_id)
        fetched_ids = ','.join(str(self.transaction_id_value(transaction)) for transaction in transactions[:8])
        self.log_event(
            'pool_transactions_repair',
            fetched_count=len(transactions),
            fetched_ids=fetched_ids if fetched_ids else 'none',
            min_transaction_id='none' if bounds is None else bounds['min_transaction_id'],
            pool_id=pool.pool_id,
            repair_start_id=repair_start_id,
        )
        await asyncio.to_thread(
            self.db.record_diagnostic_event,
            source='ticker',
            event_type='historical_repair_fetch',
            severity='info',
            pool_application=pool_application,
            pool_id=pool.pool_id,
            details={
                'repair_start_id': repair_start_id,
                'min_transaction_id': None if bounds is None else int(bounds['min_transaction_id']),
                'fetched_count': len(transactions),
                'fetched_ids_sample': [
                    int(self.transaction_id_value(transaction))
                    for transaction in transactions[:8]
                ],
            },
        )
        persisted_transactions = await self.persist_transactions(pool, transactions)
        if len(persisted_transactions) == 0:
            return

        last_watermark = last_timestamps.get(self.pool_identity(pool), (0, 0, -1))
        last_timestamps[self.pool_identity(pool)] = max(
            [self.transaction_watermark(transaction) for transaction in persisted_transactions] + [last_watermark]
        )

    async def run_iteration(self, last_timestamps):
        pools = await self.get_pools()
        await self.persist_pools(pools)

        _transactions = []
        kline_payload = {}

        for pool in pools:
            pool_identity = self.pool_identity(pool)
            await self.audit_historical_pool_history(pool)
            await self.audit_recent_pool_history(pool)
            await self.repair_historical_pool_history(pool, last_timestamps)
            await self.backfill_recent_pool_history(pool, last_timestamps)
            await self.audit_recent_pool_history(pool)
            start_id = self.resolve_transaction_start_id(pool, last_timestamps)
            transactions = await self.get_pool_transactions(pool, start_id)
            fetched_ids = ','.join(str(self.transaction_id_value(transaction)) for transaction in transactions[:8])
            self.log_event(
                'pool_transactions_fetched',
                fetched_count=len(transactions),
                fetched_ids=fetched_ids if fetched_ids else 'none',
                last_known_watermark=last_timestamps.get(pool_identity, 'none'),
                pool_id=pool.pool_id,
                requested_start_id=start_id if start_id is not None else 'none',
            )
            await asyncio.to_thread(
                self.db.record_diagnostic_event,
                source='ticker',
                event_type='incremental_fetch',
                severity='info',
                pool_application=f'{pool.pool_application.chain_id}:{pool.pool_application.owner}',
                pool_id=pool.pool_id,
                details={
                    'requested_start_id': None if start_id is None else int(start_id),
                    'fetched_count': len(transactions),
                    'fetched_ids_sample': [
                        int(self.transaction_id_value(transaction))
                        for transaction in transactions[:8]
                    ],
                    'last_known_watermark': last_timestamps.get(pool_identity),
                },
            )
            __transactions = await self.persist_transactions(pool, transactions)

            last_watermark = last_timestamps[pool_identity] if pool_identity in last_timestamps else (0, 0, -1)
            live_transactions = list(filter(
                lambda transaction: self.transaction_watermark(transaction) > last_watermark,
                __transactions,
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
            last_timestamps[pool_identity] = max(
                [self.transaction_watermark(transaction) for transaction in __transactions] + [last_watermark]
            )

        await self.manager.notify('kline', kline_payload)
        await self.manager.notify('transactions', _transactions)

    async def run(self):
        last_timestamps = await asyncio.to_thread(self.db.get_latest_transaction_watermarks)

        while self._running:
            await self.run_iteration(last_timestamps)
            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False

    def running(self):
        return self._running
