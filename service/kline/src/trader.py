import random
import time
import traceback
import asyncio
import math
import os
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

        self.regime = MarketRegime.RANGE
        self.trend_direction = TrendDirection.NONE

        # how confident the market is that we are trending
        self.trend_strength = 0.0


class Trader:
    def __init__(self, swap, wallet, meme, proxy):
        self.swap = swap
        self.wallet = wallet
        self.meme = meme
        self.proxy = proxy
        self.semaphore = asyncio.Semaphore(5)

        self.shadow_reserve_0 = None
        self.shadow_reserve_1 = None
        self.market_drift = random.gauss(0, 0.0007)
        self.market_states = {}

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
        # 1. Update market regime (slow, macro signal)
        # -------------------------------------------------
        if state.last_price <= 0 or not math.isfinite(state.last_price):
            log_return = 0.0
        else:
            ratio = price / state.last_price
            log_return = math.log(ratio) if ratio > 0 and math.isfinite(ratio) else 0.0

        # decay old belief, accumulate new evidence
        state.trend_strength *= 0.97
        state.trend_strength += abs(log_return)

        if state.regime == MarketRegime.RANGE:
            if state.trend_strength > 0.012:
                state.regime = MarketRegime.TREND
                state.trend_direction = (
                    TrendDirection.UP if log_return > 0 else TrendDirection.DOWN
                )

        elif state.regime == MarketRegime.TREND:
            if state.trend_strength < 0.004:
                state.regime = MarketRegime.RANGE
                state.trend_direction = TrendDirection.NONE

        state.last_price = price

        # -------------------------------------------------
        # 2. Anchor fair price to observed market (SAFE)
        # -------------------------------------------------
        if state.fair_price <= 0 or not math.isfinite(state.fair_price):
            # market memory corrupted → hard re-anchor
            state.fair_price = price
        else:
            ratio = price / state.fair_price
            if ratio > 0 and math.isfinite(ratio):
                state.fair_price += math.log(ratio) * 0.08
            else:
                state.fair_price = price

        # -------------------------------------------------
        # 3. Perceived mispricing (SAFE)
        # -------------------------------------------------
        ratio = state.fair_price / price
        mispricing = math.log(ratio) if ratio > 0 and math.isfinite(ratio) else 0.0

        # -------------------------------------------------
        # 4. Emotional bias depending on regime
        # -------------------------------------------------
        if state.regime == MarketRegime.RANGE:
            buy_score = mispricing
            sell_score = -mispricing
        else:
            trend_bias = 0.002 * state.trend_direction.value
            buy_score = mispricing + trend_bias
            sell_score = -mispricing - trend_bias

        # -------------------------------------------------
        # 5. Convert bias into probabilities
        # -------------------------------------------------
        def probability(score):
            return 1.0 / (1.0 + math.exp(-score / 0.0015))

        buy_probability = probability(buy_score)
        sell_probability = probability(sell_score)

        roll = random.random()
        if roll < buy_probability:
            buy_token_0 = True
        elif roll < buy_probability + sell_probability:
            buy_token_0 = False
        else:
            return (None, None)

        # -------------------------------------------------
        # 6. Trade size (trend affects intensity, not direction)
        # -------------------------------------------------
        base_size = random.lognormvariate(-0.4, 0.8)

        if state.regime == MarketRegime.TREND:
            is_trend_aligned = (
                (buy_token_0 and state.trend_direction == TrendDirection.UP) or
                (not buy_token_0 and state.trend_direction == TrendDirection.DOWN)
            )
            size = base_size * (1.2 if is_trend_aligned else 0.7)
        else:
            size = base_size

        size = min(size, reserve_1 * 0.015)

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

        # sanity check: avoid extreme price jumps
        new_price = new_reserve_1 / new_reserve_0
        if abs(new_price - price) / price > 0.04:
            return (None, None)

        # -------------------------------------------------
        # 8. Commit new reserves to macro state
        # -------------------------------------------------
        state.reserve_0 = new_reserve_0
        state.reserve_1 = new_reserve_1

        return (amount_0, amount_1)

    async def trade_in_pool(self, pool):
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

        await pool.swap(amount_0, amount_1)

    async def _trade_in_pool(self, pool):
        async with self.semaphore:
            try:
                await self.trade_in_pool(pool)
            except Exception as e:
                print(f'Failed trade token {pool.token_0} at {time.time()}: ERROR {e}')
                traceback.print_exc()

    async def trade(self) -> float:
        pools = await self.swap.get_pools()
        tasks = [self._trade_in_pool(pool) for pool in pools]
        await asyncio.gather(*tasks)

        interval = os.getenv("TRADE_INTERVAL_SECS")
        return float(interval) if interval is not None else random.uniform(5, 10)

    async def run(self):
        while True:
            start_at = time.time()
            timeout = await self.trade()
            elapsed = time.time() - start_at
            print(f'Trade pools took {elapsed} seconds')
            time.sleep(timeout)

