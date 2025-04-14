import asyncio
from swap import Pool, Transaction


class Ticker:
    def __init__(self, manager, swap, db):
        self.interval = 10 # seconds
        self.manager = manager
        self.swap = swap
        self.db = db
        self._running = True

    def get_pools(self) -> list[Pool]:
        return self.swap.get_pools()

    def get_pool_transactions(self, pool: Pool) -> list[Transaction]:
        return self.swap.get_pool_transactions(pool)

    async def run(self):
        lastTimestamps = {}

        while self._running:
            pools = self.get_pools()
            self.db.new_pools(pools)

            _transactions = []

            for pool in pools:
                transactions = self.get_pool_transactions(pool)
                __transactions = self.db.new_transactions(pool.pool_id, transactions)

                lastTimestamp = lastTimestamps[pool.pool_id] if pool.pool_id in lastTimestamps else 0

                _transactions.append({
                    'token_0': pool.token_0,
                    'token_1': pool.token_1 if pool.token_1 is not None else 'TLINERA',
                    'transactions': list(filter(lambda transaction: transaction['created_timestamp'] > lastTimestamp, __transactions)),
                })
                lastTimestamps[pool.pool_id] = max([transaction['created_timestamp'] for transaction in __transactions] + [lastTimestamp])

            await self.manager.notify('kline', None)
            await self.manager.notify('transactions', _transactions)

            await asyncio.sleep(self.interval)

    def stop(self):
        self._running = False

    def running(self):
        return self._running
