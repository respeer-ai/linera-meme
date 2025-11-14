import random
import time
import traceback


class Trader:
    def __init__(self, swap, wallet, meme):
        self.swap = swap
        self.wallet = wallet
        self.meme = meme

    def trade_amounts(self, pool, buy_token_0, token_0_balance, token_1_balance):
        reserve_0 = float(pool.reserve_0)
        reserve_1 = float(pool.reserve_1)
        token_0_balance = float(token_0_balance)
        token_1_balance = float(token_1_balance)
        token_0_price = float(pool.token_0_price)
        token_1_price = float(pool.token_1_price)

        if buy_token_0 is True and token_1_balance <= 0:
            return (None, None)
        if buy_token_0 is False and token_0_balance <= 0:
            return (None, None)

        if buy_token_0 is True:
            return (None, min(min(max(min(token_1_balance / token_0_price / 10, reserve_0 / 100), 1) * token_0_price, token_1_balance / 10), token_0_price * 10))
        if buy_token_0 is False:
            return (min(min(max(min(token_0_balance / token_1_price / 10, reserve_1 / 100), 1) * token_1_price, token_0_balance / 10), 10), None)

    async def trade_in_pool(self, pool):
        # Generate trade direction
        buy_token_0 = True if random.random() > 0.5 else False

        wallet_chain = self.wallet._chain()
        account = self.wallet.account()

        token_0_chain = await self.meme.creator_chain_id(wallet_chain, pool.token_0)
        token_1_chain = await self.meme.creator_chain_id(wallet_chain, pool.token_1) if pool.token_1 is not None else None

        token_0_balance = float(await self.meme.balance(account, token_0_chain, pool.token_0))
        token_1_balance = float(await self.wallet.balance() if pool.token_1 is None else await self.meme.balance(account, token_1_chain, pool.token_1))

        if await self.wallet.balance() < 0.001:
            print('Maker wallet balance is not enough for gas, please fund it')
            return

        if pool.token_1 is None and token_1_balance < 0.01:
            if token_0_balance < 10:
                print('Cannot exchange any more, please fund maker wallet')
                return
            buy_token_0 = False
        if token_0_balance < 10:
            buy_token_0 = True

        (amount_0, amount_1) = self.trade_amounts(pool, buy_token_0, token_0_balance, token_1_balance)

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
        print(f'      BuyToken0              {buy_token_0}')
        print(f'      DateTime               {time.time()}')

        if amount_0 is None and amount_1 is None:
            return

        await pool.swap(amount_0, amount_1)

    async def trade(self) -> float:
        pools = await self.swap.get_pools()
        for pool in pools:
            for i in range(3):
                await self.trade_in_pool(pool)
                time.sleep(1)

        return random.uniform(5, 10)

    async def run(self):
        while True:
            try:
                timeout = await self.trade()
            except Exception as e:
                timeout = 30
                print(f'Failed trade: ERROR {e}')
                traceback.print_exc()
            time.sleep(timeout)

