import random
import time
import traceback
import asyncio
import math
import os
import json

from maker_execution_policy import MakerExecutionPolicy
from maker_inventory_controller import InventoryController
from maker_minute_scheduler import MinuteScheduler
from maker_pool_market_state import PoolMarketState
from maker_reference_price_engine import ReferencePriceEngine


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
        self.max_trade_ratio = float(os.getenv("MAX_TRADE_RATIO", "0.015"))
        self.max_correction_notional_ratio = float(os.getenv("MAX_CORRECTION_NOTIONAL_RATIO", "0.0015"))
        self.max_price_impact_ratio = float(os.getenv("MAX_PRICE_IMPACT_RATIO", "0.04"))
        self.correction_strength = float(os.getenv("CORRECTION_STRENGTH", "0.55"))
        self.mispricing_threshold = float(os.getenv("MISPRICING_THRESHOLD", "0.0015"))
        self.activity_notional_ratio = float(os.getenv("ACTIVITY_NOTIONAL_RATIO", "0.00035"))
        self.max_inventory_bias_ratio = float(os.getenv("MAX_INVENTORY_BIAS_RATIO", "0.01"))
        self.max_reverse_window_fraction = float(os.getenv("MAX_REVERSE_WINDOW_FRACTION", "0.0"))
        self.reference_price_engine = ReferencePriceEngine(
            fair_price_adjustment=self.fair_price_adjustment,
            anchor_price_adjustment=self.anchor_price_adjustment,
            trend_bias_strength=self.trend_bias_strength,
        )
        self.minute_scheduler = MinuteScheduler(
            execution_window_secs=self.execution_window_secs,
            min_slices_per_window=int(os.getenv("MIN_SLICES_PER_WINDOW", "3")),
            max_slices_per_window=int(os.getenv("MAX_SLICES_PER_WINDOW", "6")),
        )
        self.execution_policy = MakerExecutionPolicy(
            max_pending_notional_ratio=self.max_pending_notional_ratio,
            max_trade_ratio=self.max_trade_ratio,
            max_correction_notional_ratio=self.max_correction_notional_ratio,
            max_price_impact_ratio=self.max_price_impact_ratio,
            correction_strength=self.correction_strength,
            mispricing_threshold=self.mispricing_threshold,
            sell_delay_compensation=self.sell_delay_compensation,
            activity_notional_ratio=self.activity_notional_ratio,
            max_inventory_bias_ratio=self.max_inventory_bias_ratio,
        )
        self.inventory_controller = InventoryController(
            pending_bias_penalty=self.pending_bias_penalty,
            long_term_bias_penalty=self.long_term_bias_penalty,
            anchor_bias_penalty=self.anchor_bias_penalty,
            long_term_bias_decay=self.long_term_bias_decay,
            max_reverse_window_fraction=self.max_reverse_window_fraction,
        )
        self.window_started_at = time.monotonic()

    def _pool_price(self, pool):
        reserve_0 = float(pool.reserve_0)
        reserve_1 = float(pool.reserve_1)
        if reserve_0 <= 0 or reserve_1 <= 0:
            return 0.0
        return reserve_1 / reserve_0

    def _pending_buy_notional(self, pool):
        return self.inventory_controller.pending_buy_notional(pool.pool_id)

    def _pending_sell_notional(self, pool):
        return self.inventory_controller.pending_sell_notional(pool.pool_id)

    def _pending_imbalance(self, pool):
        return self.inventory_controller.pending_imbalance(pool.pool_id)

    def _long_term_quote_bias(self, pool):
        return self.inventory_controller.long_term_bias(pool.pool_id)

    def _market_state(self, pool):
        state = self.market_states.get(pool.pool_id)
        if state is None:
            state = PoolMarketState(
                reserve_0=float(pool.reserve_0),
                reserve_1=float(pool.reserve_1),
            )
            self.market_states[pool.pool_id] = state
        else:
            state.update_reserves(float(pool.reserve_0), float(pool.reserve_1))
        return state

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

        state = self._market_state(pool)
        market_signal = self.reference_price_engine.update(state, price)
        long_term_bias = self.inventory_controller.strategy_bias(
            pool_id=pool.pool_id,
            reserve_quote=max(reserve_1, MIN_PRICE),
            anchor_bias=market_signal['anchor_bias'],
        )
        buy_score, sell_score = self.reference_price_engine.directional_scores(
            regime=market_signal['regime'],
            trend_direction=market_signal['trend_direction'],
            mispricing=market_signal['mispricing'],
        )
        effective_mispricing = buy_score - long_term_bias
        directional_signal = buy_score - sell_score
        if abs(directional_signal) < 1e-9:
            directional_signal = self.market_drift
        amount_0, amount_1 = self.execution_policy.decide_trade(
            reserve_0=reserve_0,
            reserve_1=reserve_1,
            token_0_balance=token_0_balance,
            token_1_balance=token_1_balance,
            pending_notional=pending_notional,
            effective_mispricing=effective_mispricing,
            directional_signal=directional_signal,
        )
        return (amount_0, amount_1)

    def queue_trade(self, pool, amount_0, amount_1):
        if amount_0 is None and amount_1 is None:
            return

        price = max(self._pool_price(pool), 1e-12)
        if amount_1 is not None:
            delta_buy = amount_1
            delta_sell = 0.0
        else:
            delta_buy = 0.0
            delta_sell = amount_0 * price
        raw_quote_notional = delta_buy - delta_sell
        quote_notional = self.inventory_controller.normalize_quote_for_window(
            pool.pool_id,
            raw_quote_notional,
        )
        if abs(quote_notional) < 1e-6:
            return
        scale = min(1.0, abs(quote_notional) / max(abs(raw_quote_notional), 1e-12))
        if amount_1 is not None:
            amount_1 *= scale
            delta_buy = amount_1
            delta_sell = 0.0
            self.inventory_controller.queue_buy_quote(pool.pool_id, delta_buy)
        else:
            amount_0 *= scale
            delta_buy = 0.0
            delta_sell = amount_0 * price
            self.inventory_controller.queue_sell_quote(pool.pool_id, delta_sell)
        net_notional = self._pending_imbalance(pool)

        print('    Queue trade ----------------------------------')
        print(f'      Pool                   {pool.pool_application.short_owner}')
        print(f'      PendingBuyQuote        {self._pending_buy_notional(pool)}')
        print(f'      PendingSellQuote       {self._pending_sell_notional(pool)}')
        print(f'      PendingNetQuote        {net_notional}')
        print(f'      DeltaBuyQuote          {delta_buy}')
        print(f'      DeltaSellQuote         {delta_sell}')
        print(f'      DateTime               {time.time()}')
        self.persist_maker_event(
            event_type='planned',
            pool=pool,
            amount_0=amount_0,
            amount_1=amount_1,
            quote_notional=quote_notional,
            details={
                'raw_quote_notional': raw_quote_notional,
                'applied_quote_notional': quote_notional,
                'applied_scale': scale,
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
            print('Maker wallet balance is not enough for gas, please fund it')
            return

        (amount_0, amount_1) = self.trade_amounts(pool, token_0_balance, token_1_balance)

        print('    Swap in pool ---------------------------------')
        print(f'      Chain                  {pool.pool_application.chain_id}')
        print(f'      Application            {pool.pool_application.short_owner}')
        print(f'      Token0                 {pool.token_0}')
        print(f'      Token1                 {pool.token_1}')
        print(f'      Reserve0               {pool.reserve_0}')
        print(f'      Reserve1               {pool.reserve_1}')
        print(f'      Token0Balance          {token_0_balance}')
        print(f'      Token1Balance          {token_1_balance}')
        print(f'      Amount0                {amount_0}')
        print(f'      Amount1                {amount_1}')
        print(f'      Token0Price            {pool.token_0_price}')
        print(f'      Token1Price            {pool.token_1_price}')
        print(f'      BuyToken0              {not amount_0}')
        print(f'      DateTime               {time.time()}')

        if amount_0 is None and amount_1 is None:
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
            print('Maker wallet balance is not enough for gas, please fund it')
            return 0.0

        price = max(self._pool_price(pool), 1e-12)

        amount_0 = None
        amount_1 = None
        if quote_notional > 0:
            amount_1 = min(quote_notional, token_1_balance * 0.30)
            if amount_1 < 1e-6:
                return 0.0
        else:
            amount_0 = min(abs(quote_notional) / price, token_0_balance * 0.30)
            if amount_0 < 1e-6:
                return 0.0

        print('    Flush trade ----------------------------------')
        print(f'      Pool                   {pool.pool_application.short_owner}')
        print(f'      QuoteNotional          {quote_notional}')
        print(f'      Amount0                {amount_0}')
        print(f'      Amount1                {amount_1}')
        print(f'      DateTime               {time.time()}')

        swap_succeeded = await pool.swap(amount_0, amount_1)
        if swap_succeeded is not True:
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
                print(f'Failed trade token {pool.token_0} at {time.time()}: ERROR {e}')
                traceback.print_exc()

    async def _flush_pool(self, pool, quote_notional):
        async with self.semaphore:
            try:
                return await self.execute_pending_in_pool(pool, quote_notional)
            except Exception as e:
                print(f'Failed flush token {pool.token_0} at {time.time()}: ERROR {e}')
                traceback.print_exc()
                return 0.0

    def _pool_ids_for_pending_state(self, pool_map: dict[int, object]) -> set[int]:
        pool_ids = set(pool_map)
        pool_ids.update(self.inventory_controller.pending_buy_quote_notional.keys())
        pool_ids.update(self.inventory_controller.pending_sell_quote_notional.keys())
        pool_ids.update(self.inventory_controller.long_term_quote_bias.keys())
        pool_ids.update(self.inventory_controller.active_minute_plans.keys())
        return pool_ids

    def prepare_slice_plans(self, pools):
        pool_map = {pool.pool_id: pool for pool in pools}
        pool_ids = self._pool_ids_for_pending_state(pool_map)
        for item in self.inventory_controller.flush_plan(pool_ids):
            pool_id = item['pool_id']
            quote_notional = item['quote_notional']
            if abs(quote_notional) < 1e-6:
                continue
            minute_plan = self.minute_scheduler.build_minute_plan(quote_notional=quote_notional)
            self.inventory_controller.set_active_minute_plan(pool_id, minute_plan)
            pool = pool_map.get(pool_id)
            if pool is not None and minute_plan is not None:
                self.persist_maker_event(
                    event_type='window_planned',
                    pool=pool,
                    quote_notional=minute_plan.quote_notional,
                    details={
                        'target_quote_notional': minute_plan.quote_notional,
                        'target_slice_count': minute_plan.target_slice_count,
                        'slice_quote_notional': list(minute_plan.slice_quotes),
                    },
                )
        self.minute_scheduler.start_new_window()

    async def execute_next_slices(self, pools):
        pool_map = {pool.pool_id: pool for pool in pools}
        tasks = []
        for pool_id in self._pool_ids_for_pending_state(pool_map):
            pool = pool_map.get(pool_id)
            if pool is None:
                continue
            quote_notional = self.inventory_controller.pop_next_slice(pool_id)
            if quote_notional is None or abs(quote_notional) < 1e-6:
                continue
            tasks.append((pool_id, pool, self._flush_pool(pool, quote_notional)))

        if tasks:
            results = await asyncio.gather(*(task for _, _, task in tasks))
            for (pool_id, _pool, _), executed_quote_notional in zip(tasks, results):
                self.inventory_controller.record_executed_quote(pool_id, executed_quote_notional)

    async def trade(self) -> float:
        pools = await self.swap.get_pools()
        tasks = [self._trade_in_pool(pool) for pool in pools]
        await asyncio.gather(*tasks)

        if self.minute_scheduler.should_finalize_window():
            self.prepare_slice_plans(pools)

        await self.execute_next_slices(pools)

        interval = os.getenv("TRADE_INTERVAL_SECS")
        return float(interval) if interval is not None else random.uniform(2, 4)

    async def run(self):
        while True:
            start_at = time.time()
            timeout = await self.trade()
            elapsed = time.time() - start_at
            print(f'Trade pools took {elapsed} seconds')
            await asyncio.sleep(timeout)
