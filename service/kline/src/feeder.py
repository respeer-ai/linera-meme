from balance import Balance
import time
import traceback


class MakerWallet:
    def __init__(self, host, chain_id):
        self.host = f'http://{host}'
        self.chain_id = chain_id

class Feeder:
    def __init__(self, swap, proxy, maker_wallets, wallet):
        self.swap = swap
        self.proxy = proxy
        self.maker_wallets = maker_wallets
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

    async def feed(self):
        # Get pools
        pools = await self.swap.get_pools()

        # Get memes
        memes = await self.proxy.get_memes()

        # Get swap balance
        swap_chain_ids = [self.swap.chain, *[pool.pool_application.chain_id for pool in pools]]
        balances = await Balance(self.swap.base_url).chain_balances(swap_chain_ids)

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
                except Exception as e:
                    print(f'Failed feed chain {chain_id}: ERROR {e}')
                    continue

        # Get proxy balance
        proxy_chain_ids = [self.proxy.chain, *[meme.chain_id for meme in memes]]
        balances = await Balance(self.proxy.base_url).chain_balances(proxy_chain_ids)

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
                except Exception as e:
                    print(f'Failed feed chain {chain_id}: ERROR {e}')
                    continue

        for maker_wallet in self.maker_wallets:
            balances = await Balance(maker_wallet.host).chain_balances([maker_wallet.chain_id])
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
                    except Exception as e:
                        print(f'Failed feed chain {chain_id}: ERROR {e}')
                        continue

    async def run(self):
        while True:
            try:
                await self.feed()
            except Exception as e:
                print(f'Failed feed: ERROR {e}')
                traceback.print_exc()
            time.sleep(30)

