from account_codec import AccountCodec
from candle_schema import INTERVAL_BUCKET_MS, build_candle_bucket_key, normalize_interval_for_api
from realtime.market_data_event import MarketDataEvent


class MarketDataPayloadBuilder:
    def __init__(
        self,
        *,
        pool_catalog_repository,
        candle_reader,
        transaction_history_repository,
        account_codec=None,
        now_ms=None,
    ):
        self.pool_catalog_repository = pool_catalog_repository
        self.candle_reader = candle_reader
        self.transaction_history_repository = transaction_history_repository
        self.account_codec = account_codec or AccountCodec()
        self.now_ms = now_ms or self._default_now_ms
        self.last_emitted_bucket_starts = {}

    def build(self, events: list[MarketDataEvent]) -> dict[str, object]:
        pools = self._affected_pools(events)
        transactions_payload = []
        kline_payload = {}
        positions_events = []

        for pool in pools:
            pool_events = self._events_for_pool(events, pool)
            trades = [event for event in pool_events if event.event_type == MarketDataEvent.TYPE_SETTLED_TRADE]
            liquidity_changes = [
                event
                for event in pool_events
                if event.event_type == MarketDataEvent.TYPE_SETTLED_LIQUIDITY_CHANGE
            ]
            finalized = [
                event
                for event in pool_events
                if event.event_type == MarketDataEvent.TYPE_CANDLE_FINALIZED
            ]
            if trades:
                pool_transactions = self._load_transactions_for_events(pool, trades)
                transactions_payload.append({
                    'token_0': pool.token_0,
                    'token_1': pool.token_1 if pool.token_1 is not None else 'TLINERA',
                    'transactions': pool_transactions,
                })
                self._merge_payload(
                    kline_payload,
                    self.build_incremental_kline_payload(pool, pool_transactions),
                )
                positions_events.append({
                    'pool_application': self.pool_application(pool),
                    'pool_id': pool.pool_id,
                    'owners': [],
                    'event_types': [MarketDataEvent.TYPE_SETTLED_TRADE],
                    'updated_at': max(
                        [
                            event.updated_at_ms
                            for event in trades
                            if event.updated_at_ms is not None
                        ] or [None]
                    ),
                })
            if finalized:
                self._merge_payload(kline_payload, self.build_rollover_kline_payload(pool, finalized))
            for event in liquidity_changes:
                positions_events.append({
                    'pool_application': self.pool_application(pool),
                    'pool_id': pool.pool_id,
                    'owners': [event.owner] if event.owner is not None else [],
                    'event_types': [event.event_type],
                    'updated_at': event.updated_at_ms,
                })

        return {
            'transactions': transactions_payload,
            'kline': kline_payload,
            'positions': {'events': positions_events},
        }

    def build_incremental_kline_payload(self, pool, transactions: list[dict]) -> dict:
        payload = {}
        seen = set()
        pool_application = self.pool_application(pool)

        for transaction in transactions:
            if transaction['transaction_type'] not in ['BuyToken0', 'SellToken0']:
                continue

            for token_reversed in [False, True]:
                token_0 = pool.token_1 if token_reversed else pool.token_0
                token_1 = pool.token_0 if token_reversed else (pool.token_1 if pool.token_1 is not None else 'TLINERA')

                for interval, bucket_ms in INTERVAL_BUCKET_MS.items():
                    bucket_key = build_candle_bucket_key(
                        pool_application=pool_application,
                        pool_id=pool.pool_id,
                        token_reversed=token_reversed,
                        interval=interval,
                        created_at_ms=int(transaction['created_at']),
                    )
                    dedupe_key = (token_0, token_1, interval, bucket_key.bucket_start_ms)
                    if dedupe_key in seen:
                        continue

                    stream_key = (pool.pool_id, pool_application, token_0, token_1, interval)
                    last_emitted_bucket_start = self.last_emitted_bucket_starts.get(stream_key)
                    range_start = (
                        bucket_key.bucket_start_ms
                        if last_emitted_bucket_start is None or bucket_key.bucket_start_ms <= last_emitted_bucket_start
                        else last_emitted_bucket_start
                    )
                    points = self.load_candle_points(
                        token_0=token_0,
                        token_1=token_1,
                        start_at=range_start,
                        end_at=bucket_key.bucket_start_ms + bucket_ms - 1,
                        interval=interval,
                        pool_id=pool.pool_id,
                        pool_application=pool_application,
                    )
                    if not points:
                        continue

                    seen.add(dedupe_key)
                    api_interval = normalize_interval_for_api(interval)
                    interval_points = payload.get(api_interval, [])
                    interval_points.append({
                        'pool_id': pool.pool_id,
                        'pool_application': pool_application,
                        'token_0': token_0,
                        'token_1': token_1,
                        'interval': api_interval,
                        'start_at': range_start,
                        'end_at': bucket_key.bucket_start_ms + bucket_ms - 1,
                        'points': points,
                    })
                    payload[api_interval] = interval_points
                    self.last_emitted_bucket_starts[stream_key] = max(
                        int(point['bucket_start_ms'])
                        for point in points
                    )

        return payload

    def build_rollover_kline_payload(self, pool, events: list[MarketDataEvent]) -> dict:
        payload = {}
        now_ms = self.now_ms()
        pool_application = self.pool_application(pool)

        for token_reversed in [False, True]:
            token_0 = pool.token_1 if token_reversed else pool.token_0
            token_1 = pool.token_0 if token_reversed else (pool.token_1 if pool.token_1 is not None else 'TLINERA')

            for interval, bucket_ms in INTERVAL_BUCKET_MS.items():
                interval_events = [
                    event
                    for event in events
                    if event.interval in (None, interval)
                ]
                if not interval_events:
                    continue
                stream_key = (pool.pool_id, pool_application, token_0, token_1, interval)
                last_emitted_bucket_start = self.last_emitted_bucket_starts.get(stream_key)

                event_bucket_starts = [
                    int(event.event_time_ms)
                    for event in interval_events
                    if event.event_time_ms is not None
                ]
                if event_bucket_starts:
                    last_finalized_bucket_start = max(event_bucket_starts)
                else:
                    current_bucket_start = build_candle_bucket_key(
                        pool_application=pool_application,
                        pool_id=pool.pool_id,
                        token_reversed=token_reversed,
                        interval=interval,
                        created_at_ms=now_ms,
                    ).bucket_start_ms
                    last_finalized_bucket_start = current_bucket_start - bucket_ms

                if (
                    last_emitted_bucket_start is not None
                    and last_finalized_bucket_start <= last_emitted_bucket_start
                ):
                    continue

                range_start = (
                    last_finalized_bucket_start
                    if last_emitted_bucket_start is None
                    else last_emitted_bucket_start + bucket_ms
                )
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
                if not points:
                    continue

                api_interval = normalize_interval_for_api(interval)
                interval_points = payload.get(api_interval, [])
                interval_points.append({
                    'pool_id': pool.pool_id,
                    'pool_application': pool_application,
                    'token_0': token_0,
                    'token_1': token_1,
                    'interval': api_interval,
                    'start_at': range_start,
                    'end_at': range_end + bucket_ms - 1,
                    'points': points,
                })
                payload[api_interval] = interval_points
                self.last_emitted_bucket_starts[stream_key] = max(
                    int(point['bucket_start_ms'])
                    for point in points
                )

        return payload

    def load_candle_points(self, **kwargs) -> list[dict]:
        return self.candle_reader.get_points(**kwargs)['points']

    def pool_application(self, pool) -> str:
        return self.account_codec.format_account(
            chain_id=pool.pool_application.chain_id,
            owner=pool.pool_application.owner,
        )

    def _affected_pools(self, events: list[MarketDataEvent]) -> list:
        target_applications = {
            event.pool_application
            for event in events
            if event.pool_application is not None
        }
        if not target_applications:
            return []
        return [
            pool
            for pool in self.pool_catalog_repository.list_current_pool_views()
            if self.pool_application(pool) in target_applications
        ]

    def _events_for_pool(self, events: list[MarketDataEvent], pool) -> list[MarketDataEvent]:
        pool_application = self.pool_application(pool)
        return [
            event
            for event in events
            if event.pool_application == pool_application
        ]

    def _load_transactions_for_events(self, pool, events: list[MarketDataEvent]) -> list[dict]:
        transaction_ids = {
            event.transaction_id
            for event in events
            if event.transaction_id is not None
        }
        if not transaction_ids:
            return []
        transactions = self.transaction_history_repository.get_pool_transactions_by_ids(
            pool_application=self.pool_application(pool),
            pool_id=pool.pool_id,
            transaction_ids=transaction_ids,
        )
        return transactions or []

    def _merge_payload(self, target: dict, source: dict) -> None:
        for interval, interval_points in source.items():
            target.setdefault(interval, []).extend(interval_points)

    def _default_now_ms(self) -> int:
        return int(__import__('time').time() * 1000)
