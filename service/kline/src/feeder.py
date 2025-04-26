from balance import Balance
import time

class Feeder:
    def __init__(self, swap, proxy, wallet):
        self.swap = swap
        self.proxy = proxy
        self.wallet = wallet
        self.threshold = 10

    def feed_chain(self, funder_chain_id, chain_id):
        try:
            # Transfer to chain
            self.wallet.transfer_with_cli(funder_chain_id, chain_id, "19")
            print(f'Feeded chain {chain_id}')
        except Exception as e:
            print(f'Failed feed {chain_id}')
            raise e

    def feed(self):
        # Get pools
        pools = self.swap.get_pools()

        # Get memes
        memes = self.proxy.get_memes()

        # Get swap balance
        swap_chain_ids = [self.swap.chain, *[pool.pool_application.chain_id for pool in pools]]
        balances = Balance(self.swap.base_url).chain_balances(swap_chain_ids)

        funded_chains = 0
        funder_chain_id = None

        for chain_id, balance in balances.items():
            if balance < self.threshold:
                if funded_chains % 5 == 0:
                    # Claim new chain
                    try:
                        funder_chain_id = self.wallet.open_chain_with_cli()
                    except Exception as e:
                        print(f'Failed open chain: {e}')
                        time.sleep(30)
                        continue
                try:
                    self.feed_chain(funder_chain_id, chain_id)
                    funded_chains += 1
                except:
                    continue

        # Get proxy balance
        proxy_chain_ids = [self.proxy.chain, *[meme.chain_id for meme in memes]]
        balances = Balance(self.proxy.base_url).chain_balances(proxy_chain_ids)

        for chain_id, balance in balances.items():
            if balance < self.threshold:
                if funded_chains % 5 == 0:
                    # Claim new chain
                    try:
                        funder_chain_id = self.wallet.open_chain_with_cli()
                    except Exception as e:
                        print(f'Failed open chain: {e}')
                        time.sleep(30)
                        continue
                try:
                    self.feed_chain(funder_chain_id, chain_id)
                    funded_chains += 1
                except:
                    continue


    def run(self):
        while True:
            self.feed()
            time.sleep(30)

