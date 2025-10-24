import random
import time


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

    def trade_in_pool(self, pool):
        # Generate trade direction
        buy_token_0 = True if random.random() > 0.5 else False

        wallet_chain = self.wallet._chain()
        account = self.wallet.account()

        token_0_chain = self.meme.creator_chain_id(wallet_chain, pool.token_0)
        token_1_chain = self.meme.creator_chain_id(wallet_chain, pool.token_1) if pool.token_1 is not None else None

        token_0_balance = self.meme.balance(account, token_0_chain, pool.token_0)
        token_1_balance = self.wallet.balance() if pool.token_1 is None else self.meme.balance(account, token_1_chain, pool.token_1)

        if pool.token_1 is None and token_1_balance < 0.1:
            buy_token_0 = False

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

        pool.swap(amount_0, amount_1)

    def trade(self) -> float:
        pools = self.swap.get_pools()
        for pool in pools:
            for i in range(3):
                self.trade_in_pool(pool)

        return random.uniform(5, 10)

    def run(self):
        while True:
            timeout = self.trade()
            time.sleep(timeout)

