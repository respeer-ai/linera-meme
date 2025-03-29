import asyncio
from swap import Pool, Transaction


class Ticker:
    def __init__(self, manager, swap, db):
        self.interval = 60 # seconds
        self.manager = manager
        self.swap = swap
        self.db = db
        self.running = True

    def get_pools(self) -> list[Pool]:
        return self.swap.get_pools()

    def get_pool_transactions(self, pool: Pool) -> list[Transaction]:
        return self.swap.get_pool_transactions(pool)

    async def run(self):
        while self.running:
            pools = self.get_pools()
            self.db.new_pools(pools)

            for pool in pools:
                transactions = self.get_pool_transactions(pool)
                self.db.new_transactions(pool.pool_id, transactions)

            await self.manager.notify()
            await asyncio.sleep(self.interval)

    def stop(self):
        self.running = Flase
