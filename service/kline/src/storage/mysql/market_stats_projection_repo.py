import time
from decimal import Decimal

from storage.mysql.pool_catalog_projection_repo import PoolCatalogProjectionRepository
from storage.mysql.pool_metadata_projection_resolver import PoolMetadataProjectionResolver
from storage.mysql.pool_state_projection_repo import PoolStateProjectionRepository


class MarketStatsProjectionRepository:
    DISPLAY_AMOUNT_SCALE = Decimal('1000000000000000000')

    def __init__(self, db, *, metadata_resolver=None):
        self.db = db
        self.metadata_resolver = (
            metadata_resolver
            or PoolMetadataProjectionResolver(
                pool_catalog_projection_repository=PoolCatalogProjectionRepository(
                    getattr(db, 'connection', db)
                ),
                pool_state_projection_repository=PoolStateProjectionRepository(db),
            )
        )

    def get_ticker(self, *, interval: str) -> list[dict]:
        start_at, end_at = self._interval_bounds(interval)
        trades = self._load_settled_trade_rows(
            start_at=start_at,
            end_at=end_at,
        )
        latest_native_prices = self._load_native_price_map()

        stats_by_token = {}
        for trade in trades:
            turnover = self._market_turnover_native(
                trade,
                latest_native_prices=latest_native_prices,
            )
            if turnover is None:
                continue
            for token, price in self._expanded_token_price_rows(trade):
                if token == 'TLINERA':
                    continue
                entry = stats_by_token.get(token)
                if entry is None:
                    entry = {
                        'token': token,
                        'high': price,
                        'low': price,
                        'volume': Decimal('0'),
                        'tx_count': 0,
                        'price_now': price,
                        'price_start': price,
                        '_first_created_at': int(trade['trade_time_ms']),
                        '_last_created_at': int(trade['trade_time_ms']),
                    }
                    stats_by_token[token] = entry
                entry['high'] = max(entry['high'], price)
                entry['low'] = min(entry['low'], price)
                entry['volume'] += turnover
                entry['tx_count'] += 1
                created_at = int(trade['trade_time_ms'])
                if created_at >= entry['_last_created_at']:
                    entry['_last_created_at'] = created_at
                    entry['price_now'] = price
                if created_at <= entry['_first_created_at']:
                    entry['_first_created_at'] = created_at
                    entry['price_start'] = price

        rows = []
        for entry in stats_by_token.values():
            rows.append({
                'token': entry['token'],
                'high': float(entry['high']),
                'low': float(entry['low']),
                'volume': float(entry['volume']),
                'tx_count': int(entry['tx_count']),
                'price_now': float(entry['price_now']),
                'price_start': float(entry['price_start']),
            })
        rows.sort(key=lambda row: row['volume'], reverse=True)
        return rows

    def get_pool_stats(self, *, interval: str) -> list[dict]:
        start_at, end_at = self._interval_bounds(interval)
        trades = self._load_settled_trade_rows(
            start_at=start_at,
            end_at=end_at,
        )

        stats_by_pool = {}
        for trade in trades:
            key = (trade['pool_application'], int(trade['pool_id']))
            price = self._trade_price(trade)
            quote_volume = self._quote_volume(trade)
            entry = stats_by_pool.get(key)
            if entry is None:
                entry = {
                    'pool_id': int(trade['pool_id']),
                    'pool_application': trade['pool_application'],
                    'token_0': trade['token_0'],
                    'token_1': trade['token_1'],
                    'high': price,
                    'low': price,
                    'volume': Decimal('0'),
                    'tx_count': 0,
                    'price_now': price,
                    'price_start': price,
                    '_first_created_at': int(trade['trade_time_ms']),
                    '_last_created_at': int(trade['trade_time_ms']),
                }
                stats_by_pool[key] = entry
            entry['high'] = max(entry['high'], price)
            entry['low'] = min(entry['low'], price)
            entry['volume'] += quote_volume
            entry['tx_count'] += 1
            created_at = int(trade['trade_time_ms'])
            if created_at >= entry['_last_created_at']:
                entry['_last_created_at'] = created_at
                entry['price_now'] = price
            if created_at <= entry['_first_created_at']:
                entry['_first_created_at'] = created_at
                entry['price_start'] = price

        rows = []
        for entry in stats_by_pool.values():
            rows.append({
                'pool_id': entry['pool_id'],
                'pool_application': entry['pool_application'],
                'token_0': entry['token_0'],
                'token_1': entry['token_1'],
                'high': float(entry['high']),
                'low': float(entry['low']),
                'volume': float(entry['volume']),
                'tx_count': int(entry['tx_count']),
                'price_now': float(entry['price_now']),
                'price_start': float(entry['price_start']),
            })
        rows.sort(key=lambda row: row['volume'], reverse=True)
        return rows

    def get_protocol_stats(self, *, pools: list[dict]) -> dict:
        current_start_at, end_at = self._interval_bounds('1d')
        previous_start_at = current_start_at - (end_at - current_start_at)

        current_trades = self._load_settled_trade_rows(
            start_at=current_start_at,
            end_at=end_at,
        )
        previous_trades = self._load_settled_trade_rows(
            start_at=previous_start_at,
            end_at=current_start_at - 1,
        )
        latest_native_prices = self._load_native_price_map()
        previous_native_prices = self._load_native_price_map(
            start_at=previous_start_at,
            end_at=current_start_at - 1,
        )

        current_volume = sum((self._quote_volume(trade) for trade in current_trades), Decimal('0'))
        previous_volume = sum((self._quote_volume(trade) for trade in previous_trades), Decimal('0'))

        if previous_volume > 0:
            volume_change = (current_volume - previous_volume) / previous_volume
        else:
            volume_change = Decimal('0')

        tvl_now = Decimal('0')
        tvl_prev = Decimal('0')
        for pool in pools:
            reserve_0 = Decimal(str(pool.get('live_reserve_0') or '0'))
            reserve_1 = Decimal(str(pool.get('live_reserve_1') or '0'))
            token_0 = str(pool.get('token_0'))
            token_1 = str(pool.get('token_1'))
            price_0_now = latest_native_prices.get(token_0, Decimal('0'))
            price_1_now = latest_native_prices.get(token_1, Decimal('0'))
            price_0_prev = previous_native_prices.get(token_0, Decimal('0'))
            price_1_prev = previous_native_prices.get(token_1, Decimal('0'))

            if price_0_now > 0:
                tvl_now += reserve_0 * price_0_now
            if price_1_now > 0:
                tvl_now += reserve_1 * price_1_now
            if price_0_prev > 0:
                tvl_prev += reserve_0 * price_0_prev
            if price_1_prev > 0:
                tvl_prev += reserve_1 * price_1_prev

        if tvl_prev > 0:
            tvl_change = (tvl_now - tvl_prev) / tvl_prev
        else:
            tvl_change = Decimal('0')

        return {
            'tvl': float(tvl_now),
            'tvl_change': float(tvl_change),
            'volume': float(current_volume),
            'volume_change': float(volume_change),
            'tx_count': len(current_trades),
            'fees': float(current_volume * Decimal('0.003')),
            'pool_count': len(pools),
        }

    def _interval_bounds(self, interval: str) -> tuple[int, int]:
        intervals = {
            '1h': 3600,
            '1d': 86400,
            '1w': 86400 * 7,
            '1m': 86400 * 30,
            '1y': 86400 * 365,
            'all': None,
        }
        if interval not in intervals:
            raise Exception('Unsupported interval')
        end_at = self._now_ms()
        if interval == 'all':
            return 0, end_at
        return end_at - intervals[interval] * 1000, end_at

    def _now_ms(self) -> int:
        if hasattr(self.db, 'now_ms'):
            return int(self.db.now_ms())
        return int(time.time() * 1000)

    def _load_settled_trade_rows(
        self,
        *,
        start_at: int | None = None,
        end_at: int | None = None,
    ) -> list[dict]:
        self.db.ensure_fresh_read_connection()
        where_clauses = []
        params = []
        if start_at is not None:
            where_clauses.append('st.trade_time_ms >= %s')
            params.append(int(start_at))
        if end_at is not None:
            where_clauses.append('st.trade_time_ms <= %s')
            params.append(int(end_at))
        where_sql = ''
        if where_clauses:
            where_sql = 'WHERE ' + ' AND '.join(where_clauses)

        self.db.cursor_dict.execute(
            f'''
                SELECT
                    st.pool_application_id AS pool_application,
                    st.trade_time_ms,
                    st.side,
                    st.amount_in,
                    st.amount_out
                FROM settled_trades st
                {where_sql}
                ORDER BY st.trade_time_ms ASC, st.transaction_id ASC, st.settled_trade_id ASC
            ''',
            tuple(params),
        )
        return self._attach_pool_metadata(list(self.db.cursor_dict.fetchall() or []))

    def _attach_pool_metadata(self, rows: list[dict]) -> list[dict]:
        metadata_by_pool_application = self.metadata_resolver.metadata_by_pool_application()
        enriched = []
        for row in rows:
            pool_application = str(row['pool_application'])
            metadata = metadata_by_pool_application.get(pool_application)
            if metadata is None:
                continue
            if metadata.get('pool_id') is None:
                continue
            enriched_row = dict(row)
            enriched_row['pool_application'] = pool_application
            enriched_row['pool_id'] = int(metadata['pool_id'])
            enriched_row['token_0'] = metadata.get('token_0')
            enriched_row['token_1'] = metadata.get('token_1')
            enriched.append(enriched_row)
        return enriched

    def _load_native_price_map(
        self,
        *,
        start_at: int | None = None,
        end_at: int | None = None,
    ) -> dict[str, Decimal]:
        native_trades = self._load_settled_trade_rows(
            start_at=start_at,
            end_at=end_at,
        )
        latest_by_token = {}
        for trade in native_trades:
            created_at = int(trade['trade_time_ms'])
            if trade['token_1'] == 'TLINERA':
                token = trade['token_0']
                price = self._trade_price(trade)
            elif trade['token_0'] == 'TLINERA':
                token = trade['token_1']
                price = self._inverse_trade_price(trade)
            else:
                continue
            previous = latest_by_token.get(token)
            if previous is None or created_at >= previous[0]:
                latest_by_token[token] = (created_at, price)
        return {
            token: payload[1]
            for token, payload in latest_by_token.items()
        }

    def _expanded_token_price_rows(self, trade: dict) -> list[tuple[str, Decimal]]:
        token_0_price = self._trade_price(trade)
        token_1_price = self._inverse_trade_price(trade)
        return [
            (trade['token_0'], token_0_price),
            (trade['token_1'], token_1_price),
        ]

    def _market_turnover_native(
        self,
        trade: dict,
        *,
        latest_native_prices: dict[str, Decimal],
    ) -> Decimal | None:
        if trade['token_1'] == 'TLINERA':
            return self._quote_volume(trade)
        if trade['token_0'] == 'TLINERA':
            return self._base_volume(trade)

        token_1_native_price = latest_native_prices.get(str(trade['token_1']))
        if token_1_native_price is not None:
            return self._quote_volume(trade) * token_1_native_price

        token_0_native_price = latest_native_prices.get(str(trade['token_0']))
        if token_0_native_price is not None:
            return self._base_volume(trade) * token_0_native_price

        return None

    def _trade_price(self, trade: dict) -> Decimal:
        side = str(trade['side'])
        amount_in = Decimal(str(trade['amount_in']))
        amount_out = Decimal(str(trade['amount_out']))
        if side == 'buy_token_0':
            return Decimal('0') if amount_out == 0 else amount_in / amount_out
        return Decimal('0') if amount_in == 0 else amount_out / amount_in

    def _inverse_trade_price(self, trade: dict) -> Decimal:
        price = self._trade_price(trade)
        return Decimal('0') if price == 0 else Decimal('1') / price

    def _base_volume(self, trade: dict) -> Decimal:
        side = str(trade['side'])
        if side == 'buy_token_0':
            return self._display_amount(trade['amount_out'])
        return self._display_amount(trade['amount_in'])

    def _quote_volume(self, trade: dict) -> Decimal:
        side = str(trade['side'])
        if side == 'buy_token_0':
            return self._display_amount(trade['amount_in'])
        return self._display_amount(trade['amount_out'])

    def _display_amount(self, value: object) -> Decimal:
        return Decimal(str(value)) / self.DISPLAY_AMOUNT_SCALE
