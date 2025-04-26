from balance import Balance
import time

class Feeder:
    def __init__(self, swap, proxy, wallet):
        self.swap = swap
        self.proxy = proxy
        self.wallet = wallet

    def feed(self):
        # Get pools
        pools = self.swap.get_pools()

        # Get memes
        memes = self.proxy.get_memes()

        # Get swap balance
        swap_chain_ids = [self.swap.chain, *[pool.pool_application.chain_id for pool in pools]]
        balances = Balance(self.swap.base_url).chain_balances(swap_chain_ids)

        for (chain_id, balance) in balances:
            print('Swap', chain_id, balance)

        # Get proxy balance
        proxy_chain_ids = [self.proxy.chain, *[meme.chain_id for meme in memes]]
        balances = Balance(self.proxy.base_url).chain_balances(proxy_chain_ids)

        for (chain_id, balance) in balances:
            print('Proxy', chain_id, balance)


    def run(self):
        while True:
            self.feed()
            time.sleep(30)

