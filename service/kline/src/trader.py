import random
import time
import traceback
import asyncio
import math
import os


class MarketState:
    drift: float
    r0: float
    f1: float

    def __init__(self, drift, r0, r1):
        self.drift = drift
        self.fair_price = float(r1 / r0)
        self.r0 = r0
        self.r1 = r1


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
        reserve_0 = float(pool.reserve_0)
        reserve_1 = float(pool.reserve_1)
        token_0_balance = float(token_0_balance)
        token_1_balance = float(token_1_balance)
        token_0_price = float(pool.token_0_price)
        token_1_price = float(pool.token_1_price)

        if pool.pool_id not in self.market_states:
            self.market_states[pool.pool_id] = MarketState(
                drift=random.gauss(0, 0.0007),
                r0=reserve_0,
                r1=reserve_1,
            )

        state = self.market_states[pool.pool_id]

        if random.random() < 0.02:
            state.drift = random.gauss(0, 0.0015)
        else:
            state.drift *= 0.995
            state.drift += random.gauss(0, 0.00015)

        state.fair_price *= math.exp(random.gauss(0, 0.0015))
        r0 = state.r0
        r1 = state.r1
        price = r1 / r0
        sigma = 0.012

        reversion = math.log(state.fair_price / price) * 0.35
        target_price = price * math.exp(state.drift + reversion + random.gauss(0, sigma))
        deviation = (target_price - price) / price

        SELL_THRESHOLD = 0.0015
        BUY_THRESHOLD  = 0.0015
        SELL_BIAS = 1.4

        if deviation > BUY_THRESHOLD:
            buy_token_0 = True
        elif deviation < -SELL_THRESHOLD * SELL_BIAS:
            buy_token_0 = False
        else:
            return (None, None)

        size = random.lognormvariate(-0.35, 0.9)
        size = min(size, r1 * 0.015)

        # We don't care about fee right now
        fee = 0.000
        k = r0 * r1

        if buy_token_0:
            if token_1_balance <= 0.01:
                return (None, None)

            amount_1 = min(size, token_1_balance * 0.15)
            if amount_1 < 1e-6:
                return (None, None)

            effective = amount_1 * (1 - fee)
            new_r1 = r1 + effective
            new_r0 = k / new_r1

            amount_0 = None
        else:
            if token_0_balance <= 0:
                return (None, None)

            amount_0 = min(size / price, token_0_balance * 0.15)
            if amount_0 < 1e-6:
                return (None, None)

            effective = amount_0 * (1 - fee)
            new_r0 = r0 + effective
            new_r1 = k / new_r0

            amount_1 = None

        new_price = new_r1 / new_r0
        if abs(new_price - price) / price > 0.04:
            return (None, None)

        state.r0 = new_r0
        state.r1 = new_r1

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

