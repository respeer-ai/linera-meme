import random
import time
import traceback
import asyncio
import math
import os
import json
from datetime import datetime
from enum import Enum


class MarketRegime(Enum):
    RANGE = "range"
    TREND = "trend"


class TrendDirection(Enum):
    UP = 1
    DOWN = -1
    NONE = 0


class MarketState:
    def __init__(self, reserve_0, reserve_1):
        self.reserve_0 = reserve_0
        self.reserve_1 = reserve_1

        self.last_price = reserve_1 / reserve_0
        self.fair_price = self.last_price
        self.anchor_price = self.last_price

        self.regime = MarketRegime.RANGE
        self.trend_direction = TrendDirection.NONE

        # how confident the market is that we are trending
        self.trend_strength = 0.0


class Trader:
    def __init__(self, swap, wallet, meme, proxy, db=None):
        self.swap = swap
        self.wallet = wallet
        self.meme = meme
        self.proxy = proxy
        self.db = db
        self.semaphore = asyncio.Semaphore(5)

        self.shadow_reserve_0 = None
        self.shadow_reserve_1 = None
        self.market_drift = random.gauss(0, 0.0007)
        self.market_states = {}
        self.pending_buy_quote_notional = {}
        self.pending_sell_quote_notional = {}
        self.long_term_quote_bias = {}
        self.execution_window_secs = float(os.getenv("TRADE_EXECUTION_WINDOW_SECS", "15"))
        self.sell_delay_compensation = float(os.getenv("SELL_DELAY_COMPENSATION", "1.12"))
        self.max_pending_notional_ratio = float(os.getenv("MAX_PENDING_NOTIONAL_RATIO", "0.03"))
        self.fair_price_adjustment = float(os.getenv("FAIR_PRICE_ADJUSTMENT", "0.08"))
        self.trend_bias_strength = float(os.getenv("TREND_BIAS_STRENGTH", "0.002"))
        self.anchor_price_adjustment = float(os.getenv("ANCHOR_PRICE_ADJUSTMENT", "0.01"))
        self.pending_bias_penalty = float(os.getenv("PENDING_BIAS_PENALTY", "0.9"))
        self.long_term_bias_penalty = float(os.getenv("LONG_TERM_BIAS_PENALTY", "1.3"))
        self.anchor_bias_penalty = float(os.getenv("ANCHOR_BIAS_PENALTY", "0.7"))
        self.long_term_bias_decay = float(os.getenv("LONG_TERM_BIAS_DECAY", "0.92"))
        self.window_started_at = time.monotonic()
        self.last_cycle_summary = {
            'reason': 'not_started',
            'pool_count': 0,
            'planned_trade_count': 0,
            'pending_pool_count': 0,
            'flush_triggered': False,
            'flush_pool_count': 0,
            'executed_pool_count': 0,
            'failed_pool_count': 0,
        }

    def _log_prefix(self):
        return f'[{datetime.now().astimezone().isoformat(timespec="milliseconds")} epoch={time.time():.3f}]'

    def _log(self, message):
        print(f'{self._log_prefix()} {message}')

    def debug_snapshot(self):
        return dict(self.last_cycle_summary)

    def _pool_price(self, pool):
        reserve_0 = float(pool.reserve_0)
        reserve_1 = float(pool.reserve_1)
        if reserve_0 <= 0 or reserve_1 <= 0:
            return 0.0
        return reserve_1 / reserve_0

    def _pending_buy_notional(self, pool):
        return self.pending_buy_quote_notional.get(pool.pool_id, 0.0)

    def _pending_sell_notional(self, pool):
        return self.pending_sell_quote_notional.get(pool.pool_id, 0.0)

    def _pending_imbalance(self, pool):
        return self._pending_buy_notional(pool) - self._pending_sell_notional(pool)

    def _long_term_quote_bias(self, pool):
        return self.long_term_quote_bias.get(pool.pool_id, 0.0)

    def persist_maker_event(self, event_type, pool, amount_0=None, amount_1=None, quote_notional=None, details=None):
        if self.db is None:
            return
        self.db.new_maker_event(
            event_type=event_type,
            pool_id=pool.pool_id,
            token_0=pool.token_0,
            token_1=pool.token_1 if pool.token_1 is not None else 'TLINERA',
            amount_0=amount_0,
            amount_1=amount_1,
            quote_notional=quote_notional,
            pool_price=self._pool_price(pool),
            details=json.dumps(details, sort_keys=True) if details is not None else None,
            created_at=int(time.time() * 1000),
        )

    def trade_amounts(self, pool, token_0_balance, token_1_balance):
        MIN_PRICE = 1e-12

        reserve_0 = float(pool.reserve_0)
        reserve_1 = float(pool.reserve_1)

        if reserve_0 <= 0 or reserve_1 <= 0:
            return (None, None)

        price = reserve_1 / reserve_0
        price = max(price, MIN_PRICE)

        token_0_balance = float(token_0_balance)
        token_1_balance = float(token_1_balance)
        pending_notional = self._pending_imbalance(pool)
        max_pending_notional = reserve_1 * self.max_pending_notional_ratio

        # -------------------------------------------------
        # Initialize market state if needed
        # -------------------------------------------------
        if pool.pool_id not in self.market_states:
            self.market_states[pool.pool_id] = MarketState(
                reserve_0=reserve_0,
                reserve_1=reserve_1,
            )

        state = self.market_states[pool.pool_id]

        # -------------------------------------------------
        # 1. Update market regime (macro trend)
        # -------------------------------------------------
        if state.last_price <= 0 or not math.isfinite(state.last_price):
            log_return = 0.0
        else:
            ratio = price / state.last_price
            log_return = math.log(ratio) if ratio > 0 and math.isfinite(ratio) else 0.0

        state.trend_strength *= 0.97
        state.trend_strength += abs(log_return)

        if state.regime == MarketRegime.RANGE:
            if state.trend_strength > 0.012:
                state.regime = MarketRegime.TREND
                state.trend_direction = (
                    TrendDirection.UP if log_return > 0 else TrendDirection.DOWN
                )

        elif state.regime == MarketRegime.TREND:
            # ⭐ 趋势疲劳：时间越久，越容易回到震荡
            state.trend_strength *= 0.995
            if state.trend_strength < 0.006:
                state.regime = MarketRegime.RANGE
                state.trend_direction = TrendDirection.NONE

        state.last_price = price

        # -------------------------------------------------
        # 2. Fair price update (LOG SPACE, SAFE)
        # -------------------------------------------------
        if state.fair_price <= 0 or not math.isfinite(state.fair_price):
            state.fair_price = price
        else:
            ratio = price / state.fair_price
            if ratio > 0 and math.isfinite(ratio):
                adjust = math.log(ratio) * self.fair_price_adjustment
                state.fair_price *= math.exp(adjust)
            else:
                state.fair_price = price

        state.fair_price = max(state.fair_price, MIN_PRICE)
        if state.anchor_price <= 0 or not math.isfinite(state.anchor_price):
            state.anchor_price = price
        else:
            ratio = price / state.anchor_price
            if ratio > 0 and math.isfinite(ratio):
                adjust = math.log(ratio) * self.anchor_price_adjustment
                state.anchor_price *= math.exp(adjust)
            else:
                state.anchor_price = price
        state.anchor_price = max(state.anchor_price, MIN_PRICE)

        # -------------------------------------------------
        # 3. Mispricing (log deviation)
        # -------------------------------------------------
        ratio = state.fair_price / price
        mispricing = math.log(ratio) if ratio > 0 and math.isfinite(ratio) else 0.0
        anchor_ratio = price / state.anchor_price
        anchor_bias = (
            math.log(anchor_ratio) if anchor_ratio > 0 and math.isfinite(anchor_ratio) else 0.0
        )
        normalized_pending_bias = pending_notional / max(reserve_1, MIN_PRICE)
        normalized_long_term_bias = self._long_term_quote_bias(pool) / max(reserve_1, MIN_PRICE)
        long_term_bias = (
            self.pending_bias_penalty * normalized_pending_bias
            + self.long_term_bias_penalty * normalized_long_term_bias
            + self.anchor_bias_penalty * anchor_bias
        )

        # -------------------------------------------------
        # 4. Bias depending on regime (trend damped by deviation)
        # -------------------------------------------------
        if state.regime == MarketRegime.RANGE:
            buy_score = mispricing
            sell_score = -mispricing
        else:
            dev = abs(mispricing)
            dev_damp = math.exp(-dev / 0.02)

            trend_bias = self.trend_bias_strength * state.trend_direction.value * dev_damp

            buy_score = mispricing + trend_bias
            sell_score = -mispricing - trend_bias

        buy_score -= long_term_bias
        sell_score += long_term_bias

        # -------------------------------------------------
        # 5. Convert bias into probabilities (normalized)
        # -------------------------------------------------
        def probability(score):
            return 1.0 / (1.0 + math.exp(-score / 0.0015))

        buy_p = probability(buy_score)
        sell_p = probability(sell_score)

        total = buy_p + sell_p
        if total > 1.0:
            buy_p /= total
            sell_p /= total

        roll = random.random()
        if roll < buy_p:
            buy_token_0 = True
        elif roll < buy_p + sell_p:
            buy_token_0 = False
        else:
            return (None, None)

        # -------------------------------------------------
        # 6. Trade size (trend affects intensity only)
        # -------------------------------------------------
        base_size = random.lognormvariate(-0.4, 0.8)

        size = base_size

        if not buy_token_0:
            size *= self.sell_delay_compensation

        size = min(size, reserve_1 * 0.015)

        if buy_token_0 and pending_notional > max_pending_notional:
            return (None, None)
        if not buy_token_0 and pending_notional < -max_pending_notional:
            return (None, None)

        # -------------------------------------------------
        # 7. AMM execution (constant product)
        # -------------------------------------------------
        k = reserve_0 * reserve_1
        fee = 0.0

        if buy_token_0:
            if token_1_balance <= 0:
                return (None, None)

            amount_1 = min(size, token_1_balance * 0.15)
            if amount_1 < 1e-6:
                return (None, None)

            effective_in = amount_1 * (1 - fee)
            new_reserve_1 = reserve_1 + effective_in
            new_reserve_0 = k / new_reserve_1

            amount_0 = None

        else:
            if token_0_balance <= 0:
                return (None, None)

            amount_0 = min(size / price, token_0_balance * 0.15)
            if amount_0 < 1e-6:
                return (None, None)

            effective_in = amount_0 * (1 - fee)
            new_reserve_0 = reserve_0 + effective_in
            new_reserve_1 = k / new_reserve_0

            amount_1 = None

        # -------------------------------------------------
        # 8. Slippage sanity check
        # -------------------------------------------------
        if price <= 0 or not math.isfinite(price):
            return (None, None)

        new_price = new_reserve_1 / new_reserve_0
        if abs(new_price - price) / price > 0.04:
            return (None, None)

        # -------------------------------------------------
        # 9. Commit macro reserves (optional state memory)
        # -------------------------------------------------
        state.reserve_0 = new_reserve_0
        state.reserve_1 = new_reserve_1

        return (amount_0, amount_1)

    def queue_trade(self, pool, amount_0, amount_1):
        if amount_0 is None and amount_1 is None:
            return

        price = max(self._pool_price(pool), 1e-12)
        if amount_1 is not None:
            delta_buy = amount_1
            delta_sell = 0.0
            self.pending_buy_quote_notional[pool.pool_id] = (
                self._pending_buy_notional(pool) + delta_buy
            )
        else:
            delta_buy = 0.0
            delta_sell = amount_0 * price
            self.pending_sell_quote_notional[pool.pool_id] = (
                self._pending_sell_notional(pool) + delta_sell
            )
        net_notional = self._pending_imbalance(pool)

        self._log('Queue trade ----------------------------------')
        self._log(f'  Pool                   {pool.pool_application.short_owner}')
        self._log(f'  PendingBuyQuote        {self._pending_buy_notional(pool)}')
        self._log(f'  PendingSellQuote       {self._pending_sell_notional(pool)}')
        self._log(f'  PendingNetQuote        {net_notional}')
        self._log(f'  DeltaBuyQuote          {delta_buy}')
        self._log(f'  DeltaSellQuote         {delta_sell}')
        self._log(f'  DateTime               {time.time()}')
        self.last_cycle_summary['planned_trade_count'] += 1
        self.last_cycle_summary['reason'] = 'trade_queued'
        self.last_cycle_summary['pending_pool_count'] = len(
            set(self.pending_buy_quote_notional) | set(self.pending_sell_quote_notional)
        )
        self.persist_maker_event(
            event_type='planned',
            pool=pool,
            amount_0=amount_0,
            amount_1=amount_1,
            quote_notional=delta_buy - delta_sell,
            details={
                'delta_buy_quote': delta_buy,
                'delta_sell_quote': delta_sell,
                'pending_buy_quote': self._pending_buy_notional(pool),
                'pending_sell_quote': self._pending_sell_notional(pool),
                'pending_net_quote': net_notional,
            },
        )

    async def plan_trade_in_pool(self, pool):
        wallet_chain = self.wallet._chain()
        account = self.wallet.account()

        token_0_chain = await self.meme.creator_chain_id(wallet_chain, pool.token_0)
        token_1_chain = await self.meme.creator_chain_id(wallet_chain, pool.token_1) if pool.token_1 is not None else None

        token_0_balance = float(await self.meme.balance(account, token_0_chain, pool.token_0))
        token_1_balance = float(await self.wallet.balance() if pool.token_1 is None else await self.meme.balance(account, token_1_chain, pool.token_1))

        if await self.wallet.balance() < 0.001:
            self._log('Maker wallet balance is not enough for gas, please fund it')
            self.last_cycle_summary['reason'] = 'wallet_low_gas'
            return

        (amount_0, amount_1) = self.trade_amounts(pool, token_0_balance, token_1_balance)

        self._log('Swap in pool ---------------------------------')
        self._log(f'  Chain                  {pool.pool_application.chain_id}')
        self._log(f'  Application            {pool.pool_application.short_owner}')
        self._log(f'  Token0                 {pool.token_0}')
        self._log(f'  Token1                 {pool.token_1}')
        self._log(f'  Reserve0               {pool.reserve_0}')
        self._log(f'  Reserve1               {pool.reserve_1}')
        self._log(f'  Token0Balance          {token_0_balance}')
        self._log(f'  Token1Balance          {token_1_balance}')
        self._log(f'  Amount0                {amount_0}')
        self._log(f'  Amount1                {amount_1}')
        self._log(f'  Token0Price            {pool.token_0_price}')
        self._log(f'  Token1Price            {pool.token_1_price}')
        self._log(f'  BuyToken0              {not amount_0}')
        self._log(f'  DateTime               {time.time()}')

        if amount_0 is None and amount_1 is None:
            self.last_cycle_summary['reason'] = 'strategy_no_trade'
            return

        self.queue_trade(pool, amount_0, amount_1)

    async def execute_pending_in_pool(self, pool, quote_notional):
        if abs(quote_notional) < 1e-6:
            return 0.0

        wallet_chain = self.wallet._chain()
        account = self.wallet.account()

        token_0_chain = await self.meme.creator_chain_id(wallet_chain, pool.token_0)
        token_1_chain = await self.meme.creator_chain_id(wallet_chain, pool.token_1) if pool.token_1 is not None else None

        token_0_balance = float(await self.meme.balance(account, token_0_chain, pool.token_0))
        token_1_balance = float(await self.wallet.balance() if pool.token_1 is None else await self.meme.balance(account, token_1_chain, pool.token_1))

        if await self.wallet.balance() < 0.001:
            self._log('Maker wallet balance is not enough for gas, please fund it')
            self.last_cycle_summary['reason'] = 'wallet_low_gas'
            return 0.0

        price = max(self._pool_price(pool), 1e-12)

        amount_0 = None
        amount_1 = None
        if quote_notional > 0:
            amount_1 = min(quote_notional, token_1_balance * 0.30)
            if amount_1 < 1e-6:
                self.last_cycle_summary['reason'] = 'quote_balance_too_small'
                return 0.0
        else:
            amount_0 = min(abs(quote_notional) / price, token_0_balance * 0.30)
            if amount_0 < 1e-6:
                self.last_cycle_summary['reason'] = 'base_balance_too_small'
                return 0.0

        self._log('Flush trade ----------------------------------')
        self._log(f'  Pool                   {pool.pool_application.short_owner}')
        self._log(f'  QuoteNotional          {quote_notional}')
        self._log(f'  Amount0                {amount_0}')
        self._log(f'  Amount1                {amount_1}')
        self._log(f'  DateTime               {time.time()}')

        swap_succeeded = await pool.swap(amount_0, amount_1)
        if swap_succeeded is not True:
            self.last_cycle_summary['failed_pool_count'] += 1
            self.last_cycle_summary['reason'] = 'swap_request_failed_or_rejected'
            self.persist_maker_event(
                event_type='failed',
                pool=pool,
                amount_0=amount_0,
                amount_1=amount_1,
                quote_notional=quote_notional,
                details={
                    'requested_quote_notional': quote_notional,
                    'reason': 'swap_request_failed_or_rejected',
                },
            )
            return 0.0
        self.last_cycle_summary['executed_pool_count'] += 1
        self.last_cycle_summary['reason'] = 'swap_executed'
        executed_quote = amount_1 if amount_1 is not None else -(amount_0 * price)
        self.persist_maker_event(
            event_type='executed',
            pool=pool,
            amount_0=amount_0,
            amount_1=amount_1,
            quote_notional=executed_quote,
            details={
                'requested_quote_notional': quote_notional,
            },
        )
        if amount_1 is not None:
            return amount_1
        return -(amount_0 * price)

    async def _trade_in_pool(self, pool):
        async with self.semaphore:
            try:
                await self.plan_trade_in_pool(pool)
            except Exception as e:
                self._log(f'Failed trade token {pool.token_0}: ERROR {e}')
                traceback.print_exc()

    async def _flush_pool(self, pool, quote_notional):
        async with self.semaphore:
            try:
                return await self.execute_pending_in_pool(pool, quote_notional)
            except Exception as e:
                self._log(f'Failed flush token {pool.token_0}: ERROR {e}')
                traceback.print_exc()
                return 0.0

    async def flush_pending_trades(self, pools):
        pool_map = {pool.pool_id: pool for pool in pools}
        tasks = []
        next_long_term_quote_bias = {}
        pool_ids = (
            set(self.pending_buy_quote_notional)
            | set(self.pending_sell_quote_notional)
            | set(self.long_term_quote_bias)
        )
        self.last_cycle_summary['flush_triggered'] = True
        self.last_cycle_summary['flush_pool_count'] = 0
        for pool_id in pool_ids:
            pool = pool_map.get(pool_id)
            decayed_bias = self.long_term_quote_bias.get(pool_id, 0.0) * self.long_term_bias_decay
            if abs(decayed_bias) >= 1e-9:
                next_long_term_quote_bias[pool_id] = decayed_bias
            quote_notional = (
                self.pending_buy_quote_notional.get(pool_id, 0.0)
                - self.pending_sell_quote_notional.get(pool_id, 0.0)
            )
            if pool is None or abs(quote_notional) < 1e-6:
                continue
            tasks.append((pool_id, pool, self._flush_pool(pool, quote_notional)))
        self.last_cycle_summary['flush_pool_count'] = len(tasks)
        if len(tasks) == 0 and self.last_cycle_summary['reason'] == 'trade_queued':
            self.last_cycle_summary['reason'] = 'pending_below_flush_threshold'

        if tasks:
            results = await asyncio.gather(*(task for _, _, task in tasks))
            for (pool_id, pool, _), executed_quote_notional in zip(tasks, results):
                updated_bias = next_long_term_quote_bias.get(pool_id, 0.0) + executed_quote_notional
                if abs(updated_bias) >= 1e-9:
                    next_long_term_quote_bias[pool_id] = updated_bias
                else:
                    next_long_term_quote_bias.pop(pool_id, None)

        self.long_term_quote_bias = next_long_term_quote_bias
        self.pending_buy_quote_notional.clear()
        self.pending_sell_quote_notional.clear()
        self.window_started_at = time.monotonic()
        self.last_cycle_summary['pending_pool_count'] = 0

    async def trade(self) -> float:
        pools = await self.swap.get_pools()
        self.last_cycle_summary = {
            'reason': 'trade_cycle_started',
            'pool_count': len(pools),
            'planned_trade_count': 0,
            'pending_pool_count': len(set(self.pending_buy_quote_notional) | set(self.pending_sell_quote_notional)),
            'flush_triggered': False,
            'flush_pool_count': 0,
            'executed_pool_count': 0,
            'failed_pool_count': 0,
        }
        if len(pools) == 0:
            self.last_cycle_summary['reason'] = 'no_pools_available'
        tasks = [self._trade_in_pool(pool) for pool in pools]
        await asyncio.gather(*tasks)

        if self.execution_window_secs <= 0 or time.monotonic() - self.window_started_at >= self.execution_window_secs:
            await self.flush_pending_trades(pools)
        elif self.last_cycle_summary['planned_trade_count'] == 0:
            self.last_cycle_summary['reason'] = 'waiting_for_trade_signal'
        else:
            self.last_cycle_summary['reason'] = 'queued_waiting_for_flush_window'

        if self.last_cycle_summary['executed_pool_count'] > 0:
            self.last_cycle_summary['reason'] = 'swap_executed'
        elif self.last_cycle_summary['failed_pool_count'] > 0:
            self.last_cycle_summary['reason'] = 'swap_request_failed_or_rejected'

        interval = os.getenv("TRADE_INTERVAL_SECS")
        return float(interval) if interval is not None else random.uniform(2, 4)

    async def run(self):
        while True:
            start_at = time.time()
            timeout = await self.trade()
            elapsed = time.time() - start_at
            self._log(f'Trade pools took {elapsed} seconds')
            await asyncio.sleep(timeout)
