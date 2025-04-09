import random
import time


class Trader:
    def __init__(self, swap, wallet, meme):
        self.swap = swap
        self.wallet = wallet
        self.meme = meme

    def trade_in_pool(self, pool):
        # Generate trade direction
        buy_token_0 = True if random.randint(0, 1) == 1 else False

        wallet_chain = self.wallet._chain()
        account = self.wallet.account()

        token_0_chain = self.meme.creator_chain_id(wallet_chain, pool.token_0)
        token_1_chain = self.meme.creator_chain_id(wallet_chain, pool.token_1) if pool.token_1 is not None else None

        token_0_balance = self.meme.balance(account, token_0_chain, pool.token_0)
        token_1_balance = self.wallet.balance() if pool.token_1 is None else self.meme.balance(account, token_1_chain, pool.token_1)

        if buy_token_0 is True and float(token_1_balance) <= 0:
            return
        if buy_token_0 is False and float(token_0_balance) <= 0:
            return

        amount_0 = str(float(token_0_balance) / 10000) if buy_token_0 is False else None
        amount_1 = str(float(token_1_balance) / 10000) if buy_token_0 is True else None

        pool.swap(amount_0, amount_1)
        print('    Swap in pool ---------------------------------')
        print(f'      Chain                  {pool.pool_application.chain_id}')
        print(f'      Application            {pool.pool_application.short_owner}')
        print(f'      Token0                 {pool.token_0}')
        print(f'      Token1                 {pool.token_1}')
        print(f'      Amount0                {amount_0}')
        print(f'      Amount1                {amount_1}')

    def trade(self) -> float:
        pools = self.swap.get_pools()
        for pool in pools:
            self.trade_in_pool(pool)

        return random.uniform(1.1, 4.9)

    def run(self):
        while True:
            timeout = self.trade()
            time.sleep(timeout)

