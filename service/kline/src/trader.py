import random
import time


class Trader:
    def __init__(self, swap, wallet, meme):
        self.swap = swap
        self.wallet = wallet
        self.meme = meme

    def trade_in_pool(self, pool):
        # Generate trade direction
        buy = True if random.randint(0, 1) == 1 else False

        account = self.wallet.account()
        native_balance = self.wallet.balance() if pool.token_1 is None else self.meme.balance()

        # TODO: get meme balance

        # TODO: trade

    def trade(self) -> float:
        pools = self.swap.get_pools()
        for pool in pools:
            self.trade_in_pool(pool)

        return random.uniform(1.1, 4.9)

    def run(self):
        while True:
            timeout = self.trade()
            time.sleep(timeout)

